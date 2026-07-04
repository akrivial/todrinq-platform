from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, conlist
from typing import List

import app.model_registry as registry
from app.services.sose9_predictions import predict_turbidity_3h
from app.routes.mock_pims import generate_sose9_data

router = APIRouter()


class SoSe9Input(BaseModel):
    # Current readings
    sensor_turbidity: float = Field(..., description="Current inlet turbidity (FTU)")
    Hag_dis: float = Field(..., description="Current Hagenhein discharge (m³/s)")
    sensor_temperature: float = Field(..., description="Current water temperature (°C)")
    month: int = Field(..., ge=1, le=12, description="Current month (1–12)")

    # 24 hourly lags for each signal (lag1 = 1h ago, lag24 = 24h ago)
    sensor_turbidity_lags: conlist(float, min_items=24, max_items=24)
    Hag_dis_lags: conlist(float, min_items=24, max_items=24)
    sensor_temperature_lags: conlist(float, min_items=24, max_items=24)
    month_lags: conlist(int, min_items=24, max_items=24)


def _to_feature_dict(inp: SoSe9Input) -> dict:
    data: dict = {
        "sensor_turbidity": inp.sensor_turbidity,
        "Hag_dis": inp.Hag_dis,
        "sensor_temperature": inp.sensor_temperature,
        "month": inp.month,
    }
    for i, v in enumerate(inp.sensor_turbidity_lags, 1):   # lag1 … lag24
        data[f"sensor_turbidity_lag{i}"] = v
    for i, v in enumerate(inp.Hag_dis_lags, 1):
        data[f"Hag_dis_lag{i}"] = v
    for i, v in enumerate(inp.sensor_temperature_lags, 1):
        data[f"sensor_temperature_lag{i}"] = v
    for i, v in enumerate(inp.month_lags, 1):
        data[f"month_lag{i}"] = v
    return data


@router.get("/overview")
def source_overview():
    return {
        "module": "Source / Intake",
        "description": "Source module for inlet conditions and source-related soft sensors.",
        "work_package": "WP4",
        "water_utility": "Waternet #DC1",
        "sensors": [
            {
                "name": "SoSe #9",
                "full_name": "Early prediction of turbidity in DWTP inlet",
                "type": "soft sensor",
                "description": "Predicts raw water turbidity 3 hours ahead (XGBoost, 24-hour lag window)",
                "status_in_platform": "Active",
                "model_loaded": registry.sose9_model is not None,
            }
        ],
    }


@router.post("/sose-9/predict")
def sose9_predict(body: SoSe9Input):
    if registry.sose9_model is None or registry.sose9_feature_cols is None:
        raise HTTPException(
            status_code=503,
            detail="SoSe #9 model not loaded. Place model artifacts in app/models/sose9/.",
        )

    feature_dict = _to_feature_dict(body)

    try:
        prediction, debug_info = predict_turbidity_3h(
            registry.sose9_model,
            registry.sose9_feature_cols,
            feature_dict,
            scaler_dict=registry.sose9_scaler_dict,
            return_debug=True,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Feature mismatch — model expects column {e}. Check features.json.",
        )

    return {
        "module": "Source / Intake",
        "sensor": "SoSe #9",
        "input_source": "manual_payload",
        "prediction_method": "real_trained_soft_sensor_model",
        "prediction": {
            "turbidity_3h_ahead_FTU": round(prediction, 4),
            "horizon_hours": 3,
            "unit": "FTU",
        },
        "debug": {
            "prediction_source": "manual_payload",
            **debug_info,
        },
        "input_summary": {
            "sensor_turbidity_current": body.sensor_turbidity,
            "Hag_dis_current": body.Hag_dis,
            "sensor_temperature_current": body.sensor_temperature,
            "month": body.month,
        },
    }


@router.get("/sose-9/latest")
def source_sose_9_latest():
    return {
        "module": "Source / Intake",
        "sensor_name": "SoSe #9",
        "full_name": "Early prediction of turbidity in DWTP inlet",
        "sensor_type": "soft sensor",
        "status": "active" if registry.sose9_model is not None else "model_not_loaded",
        "model_loaded": registry.sose9_model is not None,
    }


def _pims_to_feature_dict(d: dict) -> dict:
    data = {
        "sensor_turbidity": d["sensor_turbidity"],
        "Hag_dis": d["Hag_dis"],
        "sensor_temperature": d["sensor_temperature"],
        "month": d["month"],
    }
    for i, v in enumerate(d["sensor_turbidity_lags"], 1):
        data[f"sensor_turbidity_lag{i}"] = v
    for i, v in enumerate(d["Hag_dis_lags"], 1):
        data[f"Hag_dis_lag{i}"] = v
    for i, v in enumerate(d["sensor_temperature_lags"], 1):
        data[f"sensor_temperature_lag{i}"] = v
    for i, v in enumerate(d["month_lags"], 1):
        data[f"month_lag{i}"] = v
    return data


@router.get("/sose-9/live", summary="Predict SoSe #9 from live mock PIMS data")
def sose9_predict_live():
    if registry.sose9_model is None or registry.sose9_feature_cols is None:
        raise HTTPException(status_code=503, detail="SoSe #9 model not loaded.")

    latest = generate_sose9_data()
    feature_dict = _pims_to_feature_dict(latest)

    try:
        prediction, debug_info = predict_turbidity_3h(
            registry.sose9_model,
            registry.sose9_feature_cols,
            feature_dict,
            scaler_dict=registry.sose9_scaler_dict,
            return_debug=True,
        )
    except KeyError as e:
        raise HTTPException(status_code=422, detail=f"Feature mismatch: {e}")

    return {
        "source": "mock_pims",
        "input_source": "mock_pims",
        "prediction_method": "real_trained_soft_sensor_model",
        "sensor": "SoSe #9",
        "timestamp": latest["timestamp"],
        "input_summary": {
            "sensor_turbidity": latest["sensor_turbidity"],
            "Hag_dis": latest["Hag_dis"],
            "sensor_temperature": latest["sensor_temperature"],
            "month": latest["month"],
        },
        "prediction": {
            "turbidity_3h_ahead_FTU": round(prediction, 4),
            "horizon_hours": 3,
            "unit": "FTU",
        },
        "debug": {
            "prediction_source": "mock PIMS / live mode",
            "mock_scenario": latest.get("scenario"),
            **debug_info,
        },
    }
