from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Any, List
import json
import logging
import traceback
import joblib

log = logging.getLogger(__name__)

# Base models directory
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

# ----------------------------------------------------
# SoSe #9 — Source turbidity (3-hour forecast)
# ----------------------------------------------------
SOSE9_DIR = MODELS_DIR / "sose9"

sose9_model: Optional[Any] = None
sose9_feature_cols: Optional[List[str]] = None


sose9_scaler_dict: Optional[dict] = None


def _load_sose9() -> None:
    global sose9_model, sose9_feature_cols, sose9_scaler_dict

    model_path   = SOSE9_DIR / "xgb_sensor_hagdis_month_24_3.joblib"
    features_path = SOSE9_DIR / "features.json"
    scaler_path  = SOSE9_DIR / "scaler_dict.pkl"

    sose9_model       = _load_joblib(model_path,  "SoSe #9 model")
    sose9_scaler_dict = _load_joblib(scaler_path, "SoSe #9 scaler_dict")

    if features_path.exists():
        with open(features_path) as f:
            sose9_feature_cols = json.load(f)
        print(f">>> LOADED SoSe #9 features: {len(sose9_feature_cols)} features")
    else:
        print(f">>> MISSING SoSe #9 features.json: {features_path}")


# ----------------------------------------------------
# Ozonation model directories
# ----------------------------------------------------
OZONATION_DIR = MODELS_DIR / "ozonation"
CT_DIR = OZONATION_DIR / "ct_exposure"
BROMATE_DIR = OZONATION_DIR / "bromate"
COLIFORM_DIR = OZONATION_DIR / "coliform_removal"

# ----------------------------------------------------
# Ozonation models
# ----------------------------------------------------
ct_model: Optional[Any] = None
ct_feature_scaler: Optional[Any] = None
ct_target_scaler: Optional[Any] = None

bromate_model: Optional[Any] = None
bromate_feature_scaler: Optional[Any] = None
bromate_target_scaler: Optional[Any] = None

coliform_model: Optional[Any] = None
coliform_feature_scaler: Optional[Any] = None
coliform_target_scaler: Optional[Any] = None


def _load_joblib(path: Path, label: str) -> Optional[Any]:
    if not path.exists():
        log.warning("[models] Missing %s: %s", label, path)
        print(f">>> MISSING {label}: {path}")
        return None

    try:
        obj = joblib.load(path)
        log.info("[models] Loaded %s successfully from %s", label, path)
        print(f">>> LOADED {label}: {path}")
        return obj
    except Exception as e:
        print(f">>> FAILED TO LOAD {label}: {path}")
        print(repr(e))
        traceback.print_exc()
        log.exception("[models] Failed to load %s: %s", label, e)
        return None


def load_ozonation_models() -> None:
    global ct_model, ct_feature_scaler, ct_target_scaler
    global bromate_model, bromate_feature_scaler, bromate_target_scaler
    global coliform_model, coliform_feature_scaler, coliform_target_scaler

    # Use the same CT objects as the deployed treatment and risk routes.
    from app.services.ozonation_predictions import MODELS as deployed_ozonation_models

    deployed_ct = deployed_ozonation_models["CT"]
    ct_model = deployed_ct["model"]
    ct_feature_scaler = deployed_ct["f_scaler"]
    ct_target_scaler = deployed_ct["t_scaler"]

    bromate_model = _load_joblib(
        BROMATE_DIR / "adaboost_bromate_12_42.pkl",
        "Bromate model",
    )
    bromate_feature_scaler = _load_joblib(
        BROMATE_DIR / "feature_scaler.pkl",
        "Bromate feature scaler",
    )
    bromate_target_scaler = _load_joblib(
        BROMATE_DIR / "target_scaler.pkl",
        "Bromate target scaler",
    )

    coliform_model = _load_joblib(
        COLIFORM_DIR / "ada_logcol_7_42.pkl",
        "Coliform removal model",
    )
    coliform_feature_scaler = _load_joblib(
        COLIFORM_DIR / "feature_scaler.pkl",
        "Coliform feature scaler",
    )
    coliform_target_scaler = _load_joblib(
        COLIFORM_DIR / "target_scaler.pkl",
        "Coliform target scaler",
    )


# ----------------------------------------------------
# Coagulation model
# ----------------------------------------------------
COAG_DIR = MODELS_DIR / "coagulation"


def _load_coag() -> Optional[Any]:
    path = COAG_DIR / "optimal_model_neural_network.keras"

    print(f">>> COAG MODEL PATH: {path}")
    print(f">>> COAG MODEL EXISTS: {path.exists()}")

    if not path.exists():
        log.warning("[models] Missing coagulation model: %s", path)
        print(f">>> MISSING coagulation model: {path}")
        return None

    try:
        from tensorflow import keras
        from model.physics_layer import ModifiedBatchNormalization

        print(">>> Imported TensorFlow keras successfully")
        print(">>> Imported ModifiedBatchNormalization successfully")

        model = keras.models.load_model(
            path,
            compile=False,
            custom_objects={
                "ModifiedBatchNormalization": ModifiedBatchNormalization,
            },
        )

        log.info("[models] Coagulation model loaded successfully from %s", path)
        print(f">>> COAG MODEL LOADED OK: {path}")
        return model

    except Exception as e:
        print("\n>>> COAG LOAD ERROR >>>")
        print(repr(e))
        traceback.print_exc()
        log.exception("[models] Failed to load coagulation model: %s", e)
        return None


coag_model = _load_coag()
load_ozonation_models()
_load_sose9()


def status() -> Dict[str, bool]:
    return {
        "ct": (
            ct_model is not None
            and ct_feature_scaler is not None
            and ct_target_scaler is not None
        ),
        "bromate": (
            bromate_model is not None
            and bromate_feature_scaler is not None
            and bromate_target_scaler is not None
        ),
        "coliform_removal": (
            coliform_model is not None
            and coliform_feature_scaler is not None
            and coliform_target_scaler is not None
        ),
        "coagulation": coag_model is not None,
    }


def ready() -> bool:
    s = status()
    return (
        s["ct"]
        and s["bromate"]
        and s["coliform_removal"]
        and s["coagulation"]
    )


__all__ = [
    "ct_model",
    "ct_feature_scaler",
    "ct_target_scaler",
    "bromate_model",
    "bromate_feature_scaler",
    "bromate_target_scaler",
    "coliform_model",
    "coliform_feature_scaler",
    "coliform_target_scaler",
    "coag_model",
    "sose9_model",
    "sose9_feature_cols",
    "sose9_scaler_dict",
    "load_ozonation_models",
    "status",
    "ready",
]
