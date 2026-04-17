from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
    "description": "Predicts turbidity after coagulation",
    "status_in_platform": "Implemented",
    "work_package": "WP4",
}

RL_4 = {
    "name": "RL #4",
    "display_name": "Treatment - RL #4 - Optimal FeCl3 dosage",
    "full_name": "RL Optimal FeCl3 dosage for coagulation process",
    "type": "soft sensor",
    "process": "Coagulation",
    "description": "Recommends optimal FeCl₃ dosage",
    "status_in_platform": "Implemented",
    "work_package": "WP4",
}

SOSE_10 = {
    "name": "SoSe #10",
    "display_name": "Treatment - SoSe #10 - CT exposure prediction",
    "full_name": "Prediction of the ozonation exposure, CT, to improve the ozonation process",
    "type": "soft sensor",
    "process": "Ozonation",
    "description": "Estimates disinfection capacity (CT)",
    "status_in_platform": "Implemented",
    "work_package": "WP4",
}

SOSE_101 = {
    "name": "SoSe #10.1",
    "display_name": "Treatment - SoSe #10.1 - Bromate formation prediction",
    "full_name": "Bromate formation model",
    "type": "soft sensor",
    "process": "Ozonation",
    "description": "Predicts bromate formation risk",
    "status_in_platform": "Implemented",
    "work_package": "WP4",
}

SOSE_102 = {
    "name": "SoSe #10.2",
    "display_name": "Treatment - SoSe #10.2 - Coliform removal prediction",
    "full_name": "Coliform removal model",
    "type": "soft sensor",
    "process": "Ozonation",
    "description": "Predicts microbial removal efficiency",
    "status_in_platform": "Implemented",
    "work_package": "WP4",
}

BACTOSENSE_4 = {
    "name": "BactoSense #4",
    "display_name": "Treatment - BactoSense #4 - Hard sensor microbiological monitoring",
    "full_name": "BactoSense",
    "type": "hard sensor",
    "process": "Microbiological Monitoring",
    "description": "Real-time microbiological monitoring",
    "status_in_platform": "Connected placeholder",
    "work_package": "WP3",
}


# --------------------------------------------------
# OVERVIEW
# --------------------------------------------------
@router.get("/overview", summary="Treatment module overview")
def treatment_overview():
    return {
        "module": MODULE_NAME,
        "description": "Treatment module for coagulation, ozonation, and hard sensor monitoring.",
        "work_package": ["WP4", "WP3"],
        "water_utility": WATER_UTILITY,
        "submodules": {
            "coagulation": [
                SOSE_8,
                RL_4,
            ],
            "ozonation": [
                SOSE_10,
                SOSE_101,
                SOSE_102,
            ],
            "hard_sensors": [
                BACTOSENSE_4,
            ],
        },
    }


# --------------------------------------------------
# COAGULATION
# --------------------------------------------------
@router.get("/coagulation/latest", summary="Treatment SoSe #8 latest")
def treatment_coagulation_latest():
    try:
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
            "module": MODULE_NAME,
            "process": SOSE_8["process"],
            "sensor_name": SOSE_8["name"],
            "display_name": SOSE_8["display_name"],
            "full_name": SOSE_8["full_name"],
            "sensor_type": SOSE_8["type"],
            "description": SOSE_8["description"],
            "source": "mock_pims",
            "timestamp": latest_data["timestamp"],
            "input_data": latest_data,
            "prediction": prediction,
            "units": "model_output",
            "status": "active",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Coagulation prediction failed: {str(e)}",
        )


@router.get("/coagulation/rl/latest", summary="Treatment RL #4 latest")
def treatment_rl_4_latest():
    return {
        "module": MODULE_NAME,
        "process": RL_4["process"],
        "sensor_name": RL_4["name"],
        "display_name": RL_4["display_name"],
        "full_name": RL_4["full_name"],
        "sensor_type": RL_4["type"],
        "description": RL_4["description"],
        "status": "connected placeholder",
    }


# --------------------------------------------------
# INPUT MODELS
# --------------------------------------------------
class CTInput(BaseModel):
    Chamber: float
    WaterTemperature: float
    RFTurbidity: float
    FlowRate: float
    Ozonedosage: float


class BromateInput(BaseModel):
    month: float
    Chamber: float
    WaterTemperature: float
    RFTurbidity: float
    FlowRate: float
    Ozonedosage: float
    Residencetime: float
    WaterTemperature_1: float
    RFturbidity_1: float
    FlowRate_1: float
    Ozonedosage_1: float
    CT_All: float


class ColiformInput(BaseModel):
    Chamber: float
    WaterTemperature: float
    RFTurbidity: float
    FlowRate: float
    Ozonedosage: float
    RFturbidity_1: float
    CT_All: float


# --------------------------------------------------
# OZONATION
# --------------------------------------------------
@router.post("/ozonation/ct", summary="Treatment SoSe #10 CT")
def treatment_ozonation_ct(payload: CTInput):
    try:
        X = [[
            payload.Chamber,
            payload.WaterTemperature,
            payload.RFTurbidity,
            payload.FlowRate,
            payload.Ozonedosage,
        ]]
        result = predict_ct(X)

        return {
            "module": MODULE_NAME,
            "process": SOSE_10["process"],
            "sensor_name": SOSE_10["name"],
            "display_name": SOSE_10["display_name"],
            "full_name": SOSE_10["full_name"],
            "sensor_type": SOSE_10["type"],
            "description": SOSE_10["description"],
            "input_data": payload.model_dump(),
            "prediction": result,
            "status": "active",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"CT prediction failed: {str(e)}",
        )


@router.post("/ozonation/bromate", summary="Treatment SoSe #10.1 bromate")
def treatment_ozonation_bromate(payload: BromateInput):
    try:
        X = [[
            payload.month,
            payload.Chamber,
            payload.WaterTemperature,
            payload.RFTurbidity,
            payload.FlowRate,
            payload.Ozonedosage,
            payload.Residencetime,
            payload.WaterTemperature_1,
            payload.RFturbidity_1,
            payload.FlowRate_1,
            payload.Ozonedosage_1,
            payload.CT_All,
        ]]
        result = predict_bromate(X)

        return {
            "module": MODULE_NAME,
            "process": SOSE_101["process"],
            "sensor_name": SOSE_101["name"],
            "display_name": SOSE_101["display_name"],
            "full_name": SOSE_101["full_name"],
            "sensor_type": SOSE_101["type"],
            "description": SOSE_101["description"],
            "input_data": payload.model_dump(),
            "prediction": result,
            "status": "active",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Bromate prediction failed: {str(e)}",
        )


@router.post("/ozonation/coliform", summary="Treatment SoSe #10.2 coliform")
def treatment_ozonation_coliform(payload: ColiformInput):
    try:
        X = [[
            payload.Chamber,
            payload.WaterTemperature,
            payload.RFTurbidity,
            payload.FlowRate,
            payload.Ozonedosage,
            payload.RFturbidity_1,
            payload.CT_All,
        ]]
        result = predict_coliform(X)

        return {
            "module": MODULE_NAME,
            "process": SOSE_102["process"],
            "sensor_name": SOSE_102["name"],
            "display_name": SOSE_102["display_name"],
            "full_name": SOSE_102["full_name"],
            "sensor_type": SOSE_102["type"],
            "description": SOSE_102["description"],
            "input_data": payload.model_dump(),
            "prediction": result,
            "status": "active",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Coliform prediction failed: {str(e)}",
        )


# --------------------------------------------------
# HARD SENSOR
# --------------------------------------------------
@router.get("/hard-sensors/bactosense-4/latest", summary="Treatment BactoSense #4 latest")
def treatment_bactosense_4_latest():
    return {
        "module": MODULE_NAME,
        "process": BACTOSENSE_4["process"],
        "sensor_name": BACTOSENSE_4["name"],
        "display_name": BACTOSENSE_4["display_name"],
        "full_name": BACTOSENSE_4["full_name"],
        "sensor_type": BACTOSENSE_4["type"],
        "description": BACTOSENSE_4["description"],
        "status": "connected placeholder",
    }