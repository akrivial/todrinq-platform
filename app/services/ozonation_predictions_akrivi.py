import logging
import pandas as pd
import numpy as np

from app.data_preprocessing.ozonation.preprocessing import predict_next_step
from app.model_registry import (
    bromate_model,
    bromate_feature_scaler,
    bromate_target_scaler,
    coliform_model,
    coliform_feature_scaler,
    coliform_target_scaler,
)

logger = logging.getLogger(__name__)

# Optional rename map for future chained/raw-input workflows.
RENAME_MAP = {}

MODELS = {
    "Bromate": {
        "model": bromate_model,
        "f_scaler": bromate_feature_scaler,
        "t_scaler": bromate_target_scaler,
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
        "model": coliform_model,
        "f_scaler": coliform_feature_scaler,
        "t_scaler": coliform_target_scaler,
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


def _require_model(model_key: str) -> None:
    m_info = MODELS[model_key]
    if (
        m_info["model"] is None
        or m_info["f_scaler"] is None
        or m_info["t_scaler"] is None
    ):
        raise ValueError(f"{model_key} model or scaler is not loaded properly.")


def run_model_prediction(model_key: str, input_df: pd.DataFrame) -> float:
    _require_model(model_key)

    m_info = MODELS[model_key]
    scaler = m_info["f_scaler"]

    scaler_features = list(scaler.feature_names_in_)
    X_full = pd.DataFrame(0.0, index=input_df.index, columns=scaler_features)

    for col in input_df.columns:
        if col in X_full.columns:
            X_full[col] = input_df[col]

    X_scaled = scaler.transform(X_full)
    model_feat_indices = [scaler_features.index(c) for c in m_info["features"]]
    X_model = X_scaled[:, model_feat_indices]

    y_scaled = m_info["model"].predict(X_model)
    y_unscaled = m_info["t_scaler"].inverse_transform(
        np.array(y_scaled).reshape(-1, 1)
    ).ravel()

    return float(y_unscaled[0])


def predict_ct(X):
    raise ValueError(
        "CT model is temporarily unavailable because it depends on a missing "
        "training module (_loss). Re-enable after clean export from training."
    )


def predict_bromate(X):
    logger.info("[ozonation] Bromate input: %s", X)

    input_df = pd.DataFrame(
        X,
        columns=[
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
    )

    result = run_model_prediction("Bromate", input_df)
    logger.info("[ozonation] Bromate result: %s", result)
    return float(result)


def predict_coliform(X):
    logger.info("[ozonation] Coliform input: %s", X)

    input_df = pd.DataFrame(
        X,
        columns=[
            "Chamber",
            "WaterTemperature",
            "RFTurbidity",
            "FlowRate",
            "Ozonedosage",
            "RFturbidity_1",
            "CT_All",
        ],
    )

    k_pred = run_model_prediction("Coliform", input_df)
    time_val = float(input_df["CT_All"].values[0])
    dosage_val = float(input_df["Ozonedosage"].values[0])

    if dosage_val > 0.012:
        clog_val = (dosage_val - 0.012) / np.log10(dosage_val / 0.012)
    else:
        clog_val = 0.0

    m = 2
    coliform_val = -(k_pred * clog_val * (time_val ** m)) / np.log10(10)

    logger.info("[ozonation] Coliform result: %s", coliform_val)
    return float(coliform_val)


def predict_chained_models(new_raw_data):
    all_results = []

    for ch_id in range(1, 5):
        input_df = predict_next_step(new_raw_data, ch_id)
        if input_df is None:
            continue

        input_df = input_df.rename(columns=RENAME_MAP)

        all_results.append({
            "Chamber": ch_id,
            "CT_Prediction": None,
            "Bromate_Prediction": None,
            "Coliform_Log_Removal": None,
        })

    return pd.DataFrame(all_results)