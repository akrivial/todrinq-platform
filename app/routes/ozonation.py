from fastapi import APIRouter, HTTPException
from soft_sensors_api.app.services.ozonation_predictions_akrivi import (
    predict_ct,
    predict_bromate,
    predict_coliform,
)

router = APIRouter(prefix="/predict", tags=["Ozonation"])


@router.post("/ct")
def ct_endpoint(payload: dict):
    try:
        X = [[
            payload["Chamber"],
            payload["WaterTemperature"],
            payload["RFTurbidity"],
            payload["FlowRate"],
            payload["Ozonedosage"],
        ]]
        result = predict_ct(X)
        return {"ct_prediction": result}

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing field: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bromate")
def bromate_endpoint(payload: dict):
    try:
        X = [[
            payload["month"],
            payload["Chamber"],
            payload["WaterTemperature"],
            payload["RFTurbidity"],
            payload["FlowRate"],
            payload["Ozonedosage"],
            payload["Residencetime"],
            payload["WaterTemperature_1"],
            payload["RFturbidity_1"],
            payload["FlowRate_1"],
            payload["Ozonedosage_1"],
            payload["CT_All"],
        ]]
        result = predict_bromate(X)
        return {"bromate_prediction": result}

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing field: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/coliform")
def coliform_endpoint(payload: dict):
    try:
        X = [[
            payload["Chamber"],
            payload["WaterTemperature"],
            payload["RFTurbidity"],
            payload["FlowRate"],
            payload["Ozonedosage"],
            payload["RFturbidity_1"],
            payload["CT_All"],
        ]]
        result = predict_coliform(X)
        return {"coliform_prediction": result}

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing field: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))