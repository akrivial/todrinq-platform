from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

from app.routes.mock_pims import generate_coagulation_data, generate_coagulation_measurement
from app.model_registry import coag_model
from app.services.observation_store import record_observation

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
    storage = record_observation(
        sensor_id="coagulation_outlet_turbidity", value=prediction, unit="model_output",
        source="manual", model_version="SoSe-8", metadata={"input": body.dict()},
    )

    return {
        "sensor": "coagulation",
        "prediction": prediction,
        "units": "model_output",
        "message": "Coagulation prediction generated successfully",
        "persistence": storage,
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
    storage = record_observation(
        sensor_id="coagulation_outlet_turbidity", value=prediction, unit="model_output",
        observed_at=latest_data["timestamp"], source="mock_pims", model_version="SoSe-8",
        metadata={"input": latest_data},
    )
    measurement = generate_coagulation_measurement(latest_data["timestamp"], expected_turbidity=prediction)
    measurement_storage = record_observation(
        sensor_id="coagulation_outlet_turbidity",
        value=measurement["outlet_turbidity"],
        unit=measurement["unit"],
        observed_at=measurement["timestamp"],
        source=measurement["source"],
        kind="measurement",
        metadata={
            "quality": measurement["quality"],
            "future_source": "real_pims_outlet_turbidity",
        },
    )

    return {
        "source": "mock_pims",
        "sensor": "coagulation",
        "timestamp": latest_data["timestamp"],
        "input_data": latest_data,
        "prediction": prediction,
        "measured_outlet_turbidity": measurement["outlet_turbidity"],
        "units": "model_output",
        "message": "Live coagulation prediction generated successfully",
        "persistence": storage,
        "measurement_persistence": measurement_storage,
    }


@router.post(
    "/coagulation/history/mock",
    summary="Generate six matched hourly SoSe #8 validation samples",
)
def coagulation_mock_history(points: int = 6, interval_hours: int = 1):
    """Persist timestamp-matched model predictions and Mock-PIMS measurements."""
    safe_points = max(1, min(int(points), 48))
    safe_interval = max(1, min(int(interval_hours), 24))
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    items = []

    for offset in range(safe_points, 0, -1):
        observed_at = (now - timedelta(hours=offset * safe_interval)).isoformat()
        input_data = generate_coagulation_data(observed_at=observed_at)
        body = CoagulationInput(**{key: value for key, value in input_data.items() if key != "timestamp"})
        prediction = run_coagulation_prediction(body)
        prediction_storage = record_observation(
            sensor_id="coagulation_outlet_turbidity",
            value=prediction,
            unit="NTU / model output",
            observed_at=observed_at,
            source="mock_pims_validation_demo",
            model_version="SoSe-8",
            metadata={
                "input": input_data,
                "demonstration": True,
                "sample_timestamp": observed_at,
                "future_source": "real_pims_coagulation_inputs",
            },
        )
        measurement = generate_coagulation_measurement(observed_at, expected_turbidity=prediction)
        measurement_storage = record_observation(
            sensor_id="coagulation_outlet_turbidity",
            value=measurement["outlet_turbidity"],
            unit=measurement["unit"],
            observed_at=measurement["timestamp"],
            source=measurement["source"],
            kind="measurement",
            metadata={
                "demonstration": True,
                "quality": measurement["quality"],
                "sampling_interval_hours": safe_interval,
                "sample_timestamp": measurement["timestamp"],
                "future_source": "real_pims_outlet_turbidity",
            },
        )
        items.append({
            "timestamp": observed_at,
            "prediction": prediction,
            "measurement": measurement["outlet_turbidity"],
            "unit": measurement["unit"],
            "source": "mock_pims_coagulation_validation",
            "prediction_persistence": prediction_storage,
            "measurement_persistence": measurement_storage,
        })

    return {
        "mode": "demonstration",
        "sampling_interval_hours": safe_interval,
        "count": len(items),
        "disclaimer": "Synthetic Mock PIMS outlet measurements; the same timestamp-matching workflow will use real PIMS measurements when connected.",
        "items": items,
    }
