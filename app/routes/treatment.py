from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timedelta, timezone

from app.routes.predict import (
    CoagulationInput,
    run_coagulation_prediction,
)
from app.routes.mock_pims import (
    generate_coagulation_data,
    generate_ct_data,
    generate_ct_measurement,
    generate_bromate_data,
    generate_coliform_data,
)
from app.services.ozonation_predictions import (
    predict_ct,
    predict_bromate,
    predict_coliform,
)
from app.services.observation_store import record_observation

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
    "display_name": "Treatment - RL #5 - FeCl3 dosage advisory",
    "full_name": "RL Optimal FeCl3 dosage for coagulation process",
    "type": "reinforcement-learning advisory",
    "process": "Coagulation",
    "validation_status": "under validation",
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

CT_FEATURES = ["Chamber", "WaterTemperature", "RFTurbidity", "FlowRate", "Ozonedosage"]
BROMATE_FEATURES = [
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
]
COLIFORM_FEATURES = [
    "Chamber",
    "WaterTemperature",
    "RFTurbidity",
    "FlowRate",
    "Ozonedosage",
    "RFturbidity_1",
    "CT_All",
]


def payload_values(payload: BaseModel, features: list[str]) -> list:
    return [getattr(payload, field) for field in features]


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
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Coagulation model unavailable: {str(e)}")

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
        "status": "under validation",
        "recommended_dose": None,
        "unit": "mg/L",
        "included_in_risk_aggregation": False,
        "message": "Use POST /treatment/coagulation/rl with current process input. No fabricated latest RL recommendation is returned.",
        "validation_todos": [
            "TODO(Greg): verify ACTION_MAP, unit conversion, and model-output interpretation before final release.",
        ],
    }


# --------------------------------------------------
# CT
# --------------------------------------------------
@router.get("/ozonation/ct/latest", summary="Treatment SoSe #10 CT latest (PIMS live)")
def ct_latest():
    data = generate_ct_data()
    input_data = {k: v for k, v in data.items() if k != "timestamp"}
    try:
        body = CTInput(**input_data)
        pred = unwrap(predict_ct([payload_values(body, CT_FEATURES)]))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"CT model unavailable or scaling requires validation: {str(e)}")
    storage = record_observation(
        sensor_id="ct_exposure", value=pred, unit="mg*min/L",
        observed_at=data["timestamp"], source="mock_pims", model_version="SoSe-10",
        metadata={"input": input_data, "validation_status": "under_validation"},
    )
    return {
        "display_name": SOSE_10["display_name"],
        "input_data": input_data,
        "prediction": pred,
        "unit": "mg*min/L",
        "timestamp": data["timestamp"],
        "resolution": "1h",
        "validation_warning": "TODO(Akrivi/Greg/Alex): validate CT scaling and expected reference around 1.2 before operational display.",
        "persistence": storage,
    }


@router.post("/ozonation/ct", summary="Treatment SoSe #10 CT")
def ct(payload: CTInput):
    try:
        pred = unwrap(predict_ct([payload_values(payload, CT_FEATURES)]))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"CT model unavailable or scaling requires validation: {str(e)}")

    timestamp = datetime.now(timezone.utc).isoformat()
    storage = record_observation(
        sensor_id="ct_exposure", value=pred, unit="mg*min/L",
        observed_at=timestamp, source="manual", model_version="SoSe-10",
        metadata={"input": payload.dict(), "validation_status": "under_validation"},
    )
    return {
        "display_name": SOSE_10["display_name"],
        "prediction": pred,
        "unit": "mg*min/L",
        "timestamp": timestamp,
        "resolution": "1h",
        "validation_warning": "TODO(Akrivi/Greg/Alex): validate CT scaling and expected reference around 1.2 before operational display.",
        "persistence": storage,
    }


@router.post("/ozonation/ct/history/mock", summary="Generate five CT validation samples over 50 days")
def ct_mock_history(points: int = 5, interval_days: int = 10):
    """Create clearly-labelled mock prediction/measurement pairs for sparse CT validation."""
    safe_points = max(1, min(int(points), 12))
    safe_interval = max(1, min(int(interval_days), 90))
    now = datetime.now(timezone.utc)
    items = []
    for offset in range(safe_points, 0, -1):
        observed_at = (now - timedelta(days=offset * safe_interval)).isoformat()
        sample = generate_ct_data(observed_at=observed_at)
        input_data = {key: value for key, value in sample.items() if key != "timestamp"}
        try:
            body = CTInput(**input_data)
            prediction = unwrap(predict_ct([payload_values(body, CT_FEATURES)]))
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"CT model unavailable during mock history generation: {exc}")
        prediction_storage = record_observation(
            sensor_id="ct_exposure", value=prediction, unit="mg*min/L",
            observed_at=observed_at, source="mock_pims_validation_demo", model_version="SoSe-10",
            metadata={
                "input": input_data,
                "demonstration": True,
                "validation_status": "under_validation",
                "sample_timestamp": observed_at,
            },
        )
        # This dedicated mock measurement feed has the same interface and exact
        # sample timestamp expected from the future real PIMS/laboratory feed.
        measurement = generate_ct_measurement(observed_at, expected_ct=prediction)
        measured = measurement["CT_All"]
        measurement_storage = record_observation(
            sensor_id="ct_exposure", value=measured, unit="mg*min/L",
            observed_at=measurement["timestamp"], source=measurement["source"],
            model_version=None, kind="measurement",
            metadata={
                "demonstration": True,
                "sampling_interval_days": safe_interval,
                "quality": measurement["quality"],
                "sample_timestamp": measurement["timestamp"],
                "future_source": "real_pims_or_laboratory_ct_feed",
            },
        )
        items.append({
            "timestamp": observed_at,
            "prediction": prediction,
            "measurement": measured,
            "unit": "mg*min/L",
            "source": "mock_pims_ct_validation",
            "prediction_persistence": prediction_storage,
            "measurement_persistence": measurement_storage,
        })
    return {
        "mode": "demonstration",
        "sampling_interval_days": safe_interval,
        "disclaimer": "Five synthetic Mock PIMS CT measurements at exact 10-day sample times; the same interface will consume real PIMS/laboratory CT measurements when connected.",
        "count": len(items),
        "items": items,
    }


# --------------------------------------------------
# BROMATE
# --------------------------------------------------
@router.get("/ozonation/bromate/latest", summary="Treatment SoSe #10.1 bromate latest (PIMS live)")
def bromate_latest():
    data = generate_bromate_data()
    input_data = {k: v for k, v in data.items() if k != "timestamp"}
    try:
        body = BromateInput(**input_data)
        pred = unwrap(predict_bromate([payload_values(body, BROMATE_FEATURES)]))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Bromate model unavailable: {str(e)}")
    storage = record_observation(sensor_id="bromate_outlet", value=pred, unit="ug/L",
        observed_at=data["timestamp"], source="mock_pims", model_version="SoSe-10.1",
        metadata={"input": input_data})
    return {
        "display_name": SOSE_101["display_name"],
        "input_data": input_data,
        "prediction": pred,
        "unit": "ug/L",
        "timestamp": data["timestamp"],
        "resolution": "1h",
        "persistence": storage,
    }


@router.post("/ozonation/bromate", summary="Treatment SoSe #10.1 bromate")
def bromate(payload: BromateInput):
    try:
        pred = unwrap(predict_bromate([payload_values(payload, BROMATE_FEATURES)]))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Bromate model unavailable: {str(e)}")
    timestamp = datetime.now(timezone.utc).isoformat()
    storage = record_observation(sensor_id="bromate_outlet", value=pred, unit="ug/L",
        observed_at=timestamp, source="manual", model_version="SoSe-10.1",
        metadata={"input": payload.dict()})
    return {
        "display_name": SOSE_101["display_name"],
        "prediction": pred,
        "unit": "ug/L",
        "timestamp": timestamp,
        "persistence": storage,
    }


# --------------------------------------------------
# COLIFORM
# --------------------------------------------------
@router.get("/ozonation/coliform/latest", summary="Treatment SoSe #10.2 coliform latest (PIMS live)")
def coliform_latest():
    data = generate_coliform_data()
    input_data = {k: v for k, v in data.items() if k != "timestamp"}
    try:
        # Reproduce the delivered chained inference workflow: CT is predicted
        # first from the same process inputs, then supplied to the Holm model.
        ct_input = CTInput(**input_data)
        input_data["CT_All"] = unwrap(
            predict_ct([payload_values(ct_input, CT_FEATURES)])
        )
        body = ColiformInput(**input_data)
        pred = unwrap(predict_coliform([payload_values(body, COLIFORM_FEATURES)]))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Coliform/microbial-removal model unavailable: {str(e)}")
    storage = record_observation(sensor_id="microbial_log_reduction", value=pred,
        unit="log10 reduction", observed_at=data["timestamp"], source="mock_pims",
        model_version="SoSe-10.2-holm", metadata={
            "input": input_data,
            "interpretation": "positive log10(N_in/N_out)",
            "calculation": "Holm coefficient model plus ozone log-mean and hydraulic residence time",
        })
    return {
        "display_name": SOSE_102["display_name"],
        "input_data": input_data,
        "prediction": pred,
        "unit": "log10 reduction",
        "timestamp": data["timestamp"],
        "resolution": "1h",
        "persistence": storage,
    }


@router.post("/ozonation/coliform", summary="Treatment SoSe #10.2 coliform")
def coliform(payload: ColiformInput):
    try:
        pred = unwrap(predict_coliform([payload_values(payload, COLIFORM_FEATURES)]))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Coliform/microbial-removal model unavailable: {str(e)}")
    timestamp = datetime.now(timezone.utc).isoformat()
    storage = record_observation(sensor_id="microbial_log_reduction", value=pred,
        unit="log10 reduction", observed_at=timestamp, source="manual",
        model_version="SoSe-10.2-holm", metadata={
            "input": payload.dict(),
            "interpretation": "positive log10(N_in/N_out)",
            "calculation": "Holm coefficient model plus ozone log-mean and hydraulic residence time",
        })
    return {
        "display_name": SOSE_102["display_name"],
        "prediction": pred,
        "unit": "log10 reduction",
        "timestamp": timestamp,
        "persistence": storage,
    }


# --------------------------------------------------
# HARD SENSOR
# --------------------------------------------------
@router.get("/hard-sensors/bactosense-4/latest", summary="Treatment BactoSense #4 latest")
def bactosense():
    return {
        "display_name": BACTOSENSE_4["display_name"],
        "status": "awaiting_data",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sensor_type": "live hard-sensor connection placeholder",
        "measurements": {
            "influent_ozone": None,
            "effluent_ozone": None,
            "influent_uv": None,
            "effluent_uv": None,
            "influent_bactosense_intact_cell_number": None,
            "effluent_bactosense_intact_cell_number": None,
        },
        "timeseries": [],
        "message": "BactoSense live input is not connected yet; no operational values are fabricated.",
        "todo": "TODO(Akrivi/Greg/Alex): confirm BactoSense/PIMS tag names, units, and timestamps for influent/effluent ozone, UV, and intact cell number.",
    }
