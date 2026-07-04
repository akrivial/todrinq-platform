"""Prediction services for ozonation models.

Notes
-----
- Bromate and Coliform are loaded normally at startup.
- CT is loaded safely with try/except because the current CT artifact may fail
  due to serialization compatibility issues (e.g. NumPy random-state / MT19937).
- When a corrected CT artifact is delivered later, update only the CT_MODEL_FILENAME
  below if needed.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# Path to app/
BASE_DIR = Path(__file__).resolve().parent.parent


# -------------------------------------------------------------------
# FILE NAMES
# -------------------------------------------------------------------
# CHANGE THIS LATER ONLY if a new corrected CT file is delivered.
# Example alternatives:
# - "GB_test_5_v2_42.pkl"
# - "GB_test_5_v2_42.joblib"
# "GB_test_5_v2_42.pkl"
CT_MODEL_FILENAME = "gb_model_v3_36.pkl"

# Keep these unless your supervisor sends new scaler files too.
CT_FEATURE_SCALER_FILENAME = "feature_scaler.pkl"
CT_TARGET_SCALER_FILENAME = "target_scaler.pkl"

BROMATE_MODEL_FILENAME = "adaboost_bromate_12_42.pkl"
BROMATE_FEATURE_SCALER_FILENAME = "feature_scaler.pkl"
BROMATE_TARGET_SCALER_FILENAME = "target_scaler.pkl"

COLIFORM_MODEL_FILENAME = "ada_logcol_7_42.pkl"
COLIFORM_FEATURE_SCALER_FILENAME = "feature_scaler.pkl"
COLIFORM_TARGET_SCALER_FILENAME = "target_scaler.pkl"


# -------------------------------------------------------------------
# PATHS
# -------------------------------------------------------------------
CT_DIR = BASE_DIR / "models" / "ozonation" / "ct_exposure"
BROMATE_DIR = BASE_DIR / "models" / "ozonation" / "bromate"
COLIFORM_DIR = BASE_DIR / "models" / "ozonation" / "coliform_removal"


# -------------------------------------------------------------------
# HELPER LOADERS
# -------------------------------------------------------------------
def _load_joblib(path: Path):
    return joblib.load(path)


def _load_predictor(path: Path):
    model = _load_joblib(path)
    if not hasattr(model, "predict"):
        raise TypeError(
            f"{path.name} did not contain a predictor object. "
            f"Loaded type: {type(model).__name__}. "
            "TODO(Akrivi/Greg/Alex): provide the validated SoSe #10.1 model artifact."
        )
    return model


def _safe_load_predictor(path: Path):
    try:
        return _load_predictor(path), None
    except Exception as e:
        return None, repr(e)


def _safe_load_ct():
    """Load CT model safely.

    Returns
    -------
    tuple
        (model, error_message)
        model is None if loading failed.
    """
    try:
        model = _load_joblib(CT_DIR / CT_MODEL_FILENAME)
        return model, None
    except Exception as e:
        return None, repr(e)


# -------------------------------------------------------------------
# LOAD MODELS AND SCALERS
# -------------------------------------------------------------------
# CT is loaded safely because the current artifact may fail.
CT_MODEL, CT_LOAD_ERROR = _safe_load_ct()
BROMATE_MODEL, BROMATE_LOAD_ERROR = _safe_load_predictor(BROMATE_DIR / BROMATE_MODEL_FILENAME)
COLIFORM_MODEL, COLIFORM_LOAD_ERROR = _safe_load_predictor(COLIFORM_DIR / COLIFORM_MODEL_FILENAME)

MODELS = {
    "CT": {
        "model": CT_MODEL,
        "load_error": CT_LOAD_ERROR,
        "f_scaler": _load_joblib(CT_DIR / CT_FEATURE_SCALER_FILENAME),
        "t_scaler": _load_joblib(CT_DIR / CT_TARGET_SCALER_FILENAME),
        "features": ["Chamber", "WaterTemperature", "RFTurbidity", "FlowRate", "Ozonedosage"],
    },
    "Bromate": {
        "model": BROMATE_MODEL,
        "load_error": BROMATE_LOAD_ERROR,
        "f_scaler": _load_joblib(BROMATE_DIR / BROMATE_FEATURE_SCALER_FILENAME),
        "t_scaler": _load_joblib(BROMATE_DIR / BROMATE_TARGET_SCALER_FILENAME),
        "features": [
            "month",
            "Chamber",
            "WaterTemperature",
            "RFTurbidity",
            "FlowRate",
            "Ozonedosage",
            "Residencetime",
            "WaterTemperature_1",
            "RFturbidity_1",
            "FlowRate_1",
            "Ozonedosage_1",
            "CT_All",
        ],
    },
    "Coliform": {
        "model": COLIFORM_MODEL,
        "load_error": COLIFORM_LOAD_ERROR,
        "f_scaler": _load_joblib(COLIFORM_DIR / COLIFORM_FEATURE_SCALER_FILENAME),
        "t_scaler": _load_joblib(COLIFORM_DIR / COLIFORM_TARGET_SCALER_FILENAME),
        "features": [
            "Chamber",
            "WaterTemperature",
            "RFTurbidity",
            "FlowRate",
            "Ozonedosage",
            "RFturbidity_1",
            "CT_All",
        ],
    },
}


# -------------------------------------------------------------------
# CORE PREDICTION FUNCTION
# -------------------------------------------------------------------
def _predict_from_list(model_key: str, X: list) -> float:
    """
    Receives X as list-of-lists from the FastAPI route,
    converts to DataFrame, scales, predicts, and inverse-scales.
    """
    m_info = MODELS[model_key]

    if m_info["model"] is None:
        raise RuntimeError(
            f"{model_key} model is unavailable. "
            f"Load error: {m_info.get('load_error', 'unknown error')}"
        )

    feature_names = m_info["features"]
    input_df = pd.DataFrame(X, columns=feature_names)

    scaler = m_info["f_scaler"]
    scaler_features = list(scaler.feature_names_in_)

    # Create full input frame matching scaler expectations
    X_full = pd.DataFrame(0.0, index=input_df.index, columns=scaler_features)

    for col in input_df.columns:
        if col in X_full.columns:
            X_full[col] = input_df[col]

    X_scaled = scaler.transform(X_full)

    model_feat_indices = [scaler_features.index(col) for col in feature_names]
    X_model = X_scaled[:, model_feat_indices]

    y_scaled = m_info["model"].predict(X_model)
    y_scaled = np.asarray(y_scaled).reshape(-1, 1)

    y_unscaled = m_info["t_scaler"].inverse_transform(y_scaled).ravel()

    return float(y_unscaled[0])


# -------------------------------------------------------------------
# PUBLIC FUNCTIONS
# -------------------------------------------------------------------
def predict_ct(X: list) -> float:
    return _predict_from_list("CT", X)


def predict_bromate(X: list) -> float:
    return _predict_from_list("Bromate", X)


def predict_coliform(X: list) -> float:
    return _predict_from_list("Coliform", X)


# -------------------------------------------------------------------
# OPTIONAL STATUS HELPERS
# -------------------------------------------------------------------
def ct_available() -> bool:
    """Return True if the CT model loaded successfully."""
    return MODELS["CT"]["model"] is not None


def ct_status() -> dict:
    """Useful for debugging / status endpoints."""
    return {
        "available": ct_available(),
        "filename": CT_MODEL_FILENAME,
        "load_error": MODELS["CT"].get("load_error"),
    }
