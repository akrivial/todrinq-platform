from fastapi import APIRouter, Query

from app.services.observation_store import database_status, observation_history
from app.services.prediction_scheduler import scheduler_status


router = APIRouter(prefix="/observations", tags=["Observation History"])


@router.get("/history")
def history(sensor_id: str, limit: int = Query(48, ge=1, le=2000), kind: str | None = None):
    items = observation_history(sensor_id=sensor_id, limit=limit, kind=kind)
    return {"sensor_id": sensor_id, "count": len(items), "items": items}


@router.get("/status")
def status():
    return {**database_status(), "history_available": True, "scheduler": scheduler_status()}
