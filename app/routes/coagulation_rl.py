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


@router.post("/coagulation/rl")
def predict_coagulation_rl(data: CoagulationRLInput):
    try:
        result = get_dosage_suggestion(data.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))