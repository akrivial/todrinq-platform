"""
RL #5 coagulation recommendation API route.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone

from app.services.coagulation_rl import get_dosage_suggestion
from app.services.observation_store import record_observation
from app.routes.mock_pims import generate_coagulation_data

router = APIRouter()


def _persist_advisory(result: dict, *, source: str, timestamp: str) -> dict:
    dose = result.get("recommended_fecl3_concentration", {}).get("value")
    if dose is None:
        return result
    storage = record_observation(
        sensor_id="fecl3_dose_recommendation",
        value=float(dose),
        unit="mg/L",
        observed_at=timestamp,
        source=source,
        model_version="RL-5",
        metadata={
            "input": result.get("input_data", {}),
            "predicted_outlet_turbidity": result.get("predicted_outlet_turbidity", {}).get("value"),
            "validation_status": result.get("validation_status", "under validation"),
            "advisory_only": True,
        },
    )
    result["timestamp"] = timestamp
    result["operator_advisory"]["timestamp"] = timestamp
    result["persistence"] = storage
    return result


class CoagulationRLInput(BaseModel):
    ftu_raw_water: float
    fecl3_concentration: float
    temperature_raw_water: float
    ph_raw_water: float
    after_dredging: float
    lane: int
    year: int

    # Optional flow inputs from PIMS/mock-PIMS.
    # The service uses flow_coagulation_{lane}.
    flow_coagulation_1: float | None = None
    flow_coagulation_2: float | None = None
    flow_coagulation_3: float | None = None
    flow_coagulation_4: float | None = None


@router.post("/coagulation/rl")
def predict_coagulation_rl(data: CoagulationRLInput):
    try:
        result = get_dosage_suggestion(data.dict())
        return _persist_advisory(
            result,
            source="manual",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coagulation/rl/latest")
@router.get("/coagulation/rl/recommendation/latest")
def get_latest_coagulation_rl():
    """
    Mock latest RL #5 recommendation.

    Later this can be connected directly to /pims/coagulation/latest.
    """
    try:
        latest_mock_pims_input = generate_coagulation_data()
        lane = int(latest_mock_pims_input["lane"])
        latest_mock_pims_input[f"flow_coagulation_{lane}"] = 1000.0
        timestamp = latest_mock_pims_input.pop("timestamp")

        result = get_dosage_suggestion(latest_mock_pims_input)
        return _persist_advisory(result, source="mock_pims", timestamp=timestamp)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
