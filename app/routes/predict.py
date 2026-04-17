from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
import pandas as pd

from app.routes.mock_pims import generate_coagulation_data
from app.model_registry import coag_model

router = APIRouter(prefix="/predict", tags=["Soft Sensors"])


class CoagulationInput(BaseModel):
    ftu_raw_water: float
    fecl3_concentration: float
    temperature_raw_water: float
    ph_raw_water: float
    after_dredging: int
    lane: int
    year: int


def _build_coagulation_features(body: CoagulationInput) -> pd.DataFrame:
    """
    Current deployment feature builder.

    This keeps the exact feature order currently used by the deployed API.
    If the training pipeline requires additional preprocessing from
    waternet_preprocess.py, replace this function with the exact same logic.
    """
    return pd.DataFrame([{
        "ftu_raw_water": body.ftu_raw_water,
        "fecl3_concentration": body.fecl3_concentration,
        "temperature_raw_water": body.temperature_raw_water,
        "ph_raw_water": body.ph_raw_water,
        "after_dredging": body.after_dredging,
        "lane": body.lane,
        "year": body.year,
    }])


def run_coagulation_prediction(body: CoagulationInput) -> float:
    if coag_model is None:
        raise HTTPException(status_code=503, detail="Coagulation model not available")

    try:
        features_df = _build_coagulation_features(body)

        X = features_df[
            [
                "ftu_raw_water",
                "fecl3_concentration",
                "temperature_raw_water",
                "ph_raw_water",
                "after_dredging",
                "lane",
                "year",
            ]
        ].to_numpy(dtype=float)

        y_pred = coag_model.predict(X, verbose=0)
        prediction = float(np.array(y_pred).reshape(-1)[0])
        return prediction

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Coagulation prediction failed: {str(e)}",
        )


@router.post("/coagulation", summary="Predict coagulation process output")
def predict_coagulation(body: CoagulationInput):
    prediction = run_coagulation_prediction(body)

    return {
        "sensor": "coagulation",
        "prediction": prediction,
        "units": "model_output",
        "message": "Coagulation prediction generated successfully",
    }


@router.get(
    "/coagulation/live",
    summary="Predict coagulation output from live mock PIMS data",
)
def predict_coagulation_live():
    latest_data = generate_coagulation_data()

    body = CoagulationInput(
        ftu_raw_water=latest_data["ftu_raw_water"],
        fecl3_concentration=latest_data["fecl3_concentration"],
        temperature_raw_water=latest_data["temperature_raw_water"],
        ph_raw_water=latest_data["ph_raw_water"],
        after_dredging=latest_data["after_dredging"],
        lane=latest_data["lane"],
        year=latest_data["year"],
    )

    prediction = run_coagulation_prediction(body)

    return {
        "source": "mock_pims",
        "sensor": "coagulation",
        "timestamp": latest_data["timestamp"],
        "input_data": latest_data,
        "prediction": prediction,
        "units": "model_output",
        "message": "Live coagulation prediction generated successfully",
    }