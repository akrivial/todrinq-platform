"""
RL #5 coagulation recommendation API route.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.coagulation_rl import get_dosage_suggestion

router = APIRouter()


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
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coagulation/rl/latest")
def get_latest_coagulation_rl():
    """
    Mock latest RL #5 recommendation.

    Later this can be connected directly to /pims/coagulation/latest.
    """
    try:
        latest_mock_pims_input = {
            "ftu_raw_water": 15.2,
            "fecl3_concentration": 5.0,
            "temperature_raw_water": 16.0,
            "ph_raw_water": 7.4,
            "after_dredging": 450.0,
            "lane": 1,
            "year": 2026,
            "flow_coagulation_1": 1000.0,
        }

        result = get_dosage_suggestion(latest_mock_pims_input)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))