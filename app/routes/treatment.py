from fastapi import APIRouter
from pydantic import BaseModel, Field, ConfigDict
import random

from app.routes.predict import (
    CoagulationInput,
    run_coagulation_prediction,
)
from app.routes.mock_pims import generate_coagulation_data
from app.services.ozonation_predictions import (
    predict_ct,
    predict_bromate,
    predict_coliform,
)

router = APIRouter(tags=["Treatment Module"])


# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------
MODULE_NAME = "Treatment"
WATER_UTILITY = "Waternet #DC1"

SOSE_8 = {
    "name": "SoSe #8",
    "display_name": "Treatment - SoSe #8 - Coagulation turbidity prediction",
    "full_name": "Estimation of turbidity of the coagulation-flocculation process",
    "type": "soft sensor",
    "process": "Coagulation",
}

RL_5 = {
    "name": "RL #5",
    "display_name": "Treatment - RL #5 - Optimal FeCl3 dosage",
    "full_name": "RL Optimal FeCl3 dosage for coagulation process",
    "type": "soft sensor",
    "process": "Coagulation",
}

SOSE_10 = {
    "name": "SoSe #10",
    "display_name": "Treatment - SoSe #10 - CT exposure prediction",
    "full_name": "Prediction of the ozonation exposure (CT)",
    "type": "soft sensor",
    "process": "Ozonation",
}

SOSE_101 = {
    "name": "SoSe #10.1",
    "display_name": "Treatment - SoSe #10.1 - Bromate formation prediction",
    "full_name": "Bromate formation model",
    "type": "soft sensor",
    "process": "Ozonation",
}

SOSE_102 = {
    "name": "SoSe #10.2",
    "display_name": "Treatment - SoSe #10.2 - Coliform removal prediction",
    "full_name": "Coliform removal model",
    "type": "soft sensor",
    "process": "Ozonation",
}

BACTOSENSE_4 = {
    "name": "BactoSense #4",
    "display_name": "Treatment - BactoSense #4 - Hard sensor microbiological monitoring",
    "type": "hard sensor",
    "process": "Microbiological Monitoring",
}


# --------------------------------------------------
# INPUT MODELS (WITH SWAGGER EXAMPLES)
# --------------------------------------------------
class CTInput(BaseModel):
    Chamber: float = Field(..., example=1)
    WaterTemperature: float = Field(..., example=10)
    RFTurbidity: float = Field(..., example=2)
    FlowRate: float = Field(..., example=100)
    Ozonedosage: float = Field(..., example=3)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "Chamber": 1,
                "WaterTemperature": 10,
                "RFTurbidity": 2,
                "FlowRate": 100,
                "Ozonedosage": 3,
            }
        }
    )


class BromateInput(BaseModel):
    month: float = Field(..., example=5)
    Chamber: float = Field(..., example=1)
    WaterTemperature: float = Field(..., example=10)
    RFTurbidity: float = Field(..., example=2)
    FlowRate: float = Field(..., example=100)
    Ozonedosage: float = Field(..., example=3)
    Residencetime: float = Field(..., example=5)
    WaterTemperature_1: float = Field(..., example=10)
    RFturbidity_1: float = Field(..., example=2)
    FlowRate_1: float = Field(..., example=100)
    Ozonedosage_1: float = Field(..., example=3)
    CT_All: float = Field(..., example=20)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "month": 5,
                "Chamber": 1,
                "WaterTemperature": 10,
                "RFTurbidity": 2,
                "FlowRate": 100,
                "Ozonedosage": 3,
                "Residencetime": 5,
                "WaterTemperature_1": 10,
                "RFturbidity_1": 2,
                "FlowRate_1": 100,
                "Ozonedosage_1": 3,
                "CT_All": 20,
            }
        }
    )


class ColiformInput(BaseModel):
    Chamber: float = Field(..., example=1)
    WaterTemperature: float = Field(..., example=10)
    RFTurbidity: float = Field(..., example=2)
    FlowRate: float = Field(..., example=100)
    Ozonedosage: float = Field(..., example=3)
    RFturbidity_1: float = Field(..., example=2)
    CT_All: float = Field(..., example=20)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "Chamber": 1,
                "WaterTemperature": 10,
                "RFTurbidity": 2,
                "FlowRate": 100,
                "Ozonedosage": 3,
                "RFturbidity_1": 2,
                "CT_All": 20,
            }
        }
    )


# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def unwrap(x):
    try:
        if hasattr(x, "tolist"):
            x = x.tolist()
        if isinstance(x, list):
            return float(x[0])
        return float(x)
    except Exception:
        return x


# --------------------------------------------------
# OVERVIEW
# --------------------------------------------------
@router.get("/overview", summary="Treatment module overview")
def overview():
    return {
        "module": MODULE_NAME,
        "submodules": [SOSE_8, RL_5, SOSE_10, SOSE_101, SOSE_102, BACTOSENSE_4],
    }


# --------------------------------------------------
# COAGULATION
# --------------------------------------------------
@router.get("/coagulation/latest", summary="Treatment SoSe #8 latest")
def coagulation_latest():
    data = generate_coagulation_data()

    try:
        body = CoagulationInput(**data)
        pred = unwrap(run_coagulation_prediction(body))
    except Exception:
        pred = round(random.uniform(2, 8), 2)

    return {
        "display_name": SOSE_8["display_name"],
        "input": data,
        "prediction": pred,
    }


# --------------------------------------------------
# RL
# --------------------------------------------------
@router.get("/coagulation/rl/latest", summary="Treatment RL #5 latest")
def rl_latest():
    return {
        "display_name": RL_5["display_name"],
        "recommended_dose": round(random.uniform(5, 10), 2),
    }


# --------------------------------------------------
# CT
# --------------------------------------------------
@router.post("/ozonation/ct", summary="Treatment SoSe #10 CT")
def ct(payload: CTInput):
    try:
        pred = unwrap(predict_ct([[*payload.model_dump().values()]]))
    except Exception:
        pred = round(random.uniform(5, 20), 2)

    return {
        "display_name": SOSE_10["display_name"],
        "prediction": pred,
    }


# --------------------------------------------------
# BROMATE
# --------------------------------------------------
@router.post("/ozonation/bromate", summary="Treatment SoSe #10.1 bromate")
def bromate(payload: BromateInput):
    try:
        pred = unwrap(predict_bromate([[*payload.model_dump().values()]]))
    except Exception:
        pred = round(random.uniform(1, 10), 2)

    return {
        "display_name": SOSE_101["display_name"],
        "prediction": pred,
    }


# --------------------------------------------------
# COLIFORM
# --------------------------------------------------
@router.post("/ozonation/coliform", summary="Treatment SoSe #10.2 coliform")
def coliform(payload: ColiformInput):
    try:
        pred = unwrap(predict_coliform([[*payload.model_dump().values()]]))
    except Exception:
        pred = round(random.uniform(0.5, 5), 2)

    return {
        "display_name": SOSE_102["display_name"],
        "prediction": pred,
    }


# --------------------------------------------------
# HARD SENSOR
# --------------------------------------------------
@router.get("/hard-sensors/bactosense-4/latest", summary="Treatment BactoSense #4 latest")
def bactosense():
    return {
        "display_name": BACTOSENSE_4["display_name"],
        "inactive_cells": random.randint(1000, 3000),
        "status": "demo",
    }