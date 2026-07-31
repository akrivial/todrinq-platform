"""
RL #5 coagulation recommendation API route.
"""

import csv
import io
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from datetime import datetime, timezone

from app.services.coagulation_rl import DOSE_UNIT, get_dosage_suggestion
from app.services.observation_store import observation_history, record_observation
from app.routes.mock_pims import generate_coagulation_data

router = APIRouter()


def _persist_advisory(result: dict, *, source: str, timestamp: str) -> dict:
    dose = result.get("recommended_fecl3_concentration", {}).get("value")
    if dose is None:
        return result
    storage = record_observation(
        sensor_id="fecl3_dose_recommendation",
        value=float(dose),
        unit=result.get("recommended_fecl3_concentration", {}).get("unit", DOSE_UNIT),
        observed_at=timestamp,
        source=source,
        model_version=result.get("model_lifecycle", {}).get("model_version", "RL-5"),
        metadata={
            "input": result.get("input_data", {}),
            "input_data_timestamp": result.get("data_quality", {}).get("observed_at"),
            "current_actual_dose": result.get("current_fecl3_dose", {}).get("value"),
            "recommended_dose": dose,
            "dose_unit": result.get("recommended_fecl3_concentration", {}).get("unit", DOSE_UNIT),
            "predicted_turbidity_current_dose": result.get(
                "predicted_turbidity_current_dose", {}
            ).get("value"),
            "predicted_turbidity_recommended_dose": result.get(
                "predicted_turbidity_recommended_dose", {}
            ).get("value"),
            "operator_decision": "pending",
            "operator_decision_timestamp": None,
            "model_name": result.get("model_lifecycle", {}).get("model_name"),
            "model_version": result.get("model_lifecycle", {}).get("model_version"),
            "model_training_date": result.get("model_lifecycle", {}).get("training_date"),
            "data_quality_status": result.get("data_quality", {}).get("status"),
            "validation_status": result.get("validation_status", "under validation"),
            "advisory_only": True,
        },
    )
    result["timestamp"] = timestamp
    result["operator_advisory"]["timestamp"] = timestamp
    result["persistence"] = storage
    return result


class CoagulationRLInput(BaseModel):
    ftu_raw_water: float | None = None
    fecl3_concentration: float | None = None
    temperature_raw_water: float | None = None
    ph_raw_water: float | None = None
    after_dredging: float | None = None
    lane: int | None = None
    year: int | None = None
    input_timestamp: str | None = None
    data_status: Literal["valid", "stale", "incomplete", "unavailable", "maintenance"] | None = None
    maintenance_active: bool = False

    # Optional flow inputs from PIMS/mock-PIMS.
    # The service uses flow_coagulation_{lane}.
    flow_coagulation_1: float | None = None
    flow_coagulation_2: float | None = None
    flow_coagulation_3: float | None = None
    flow_coagulation_4: float | None = None


@router.post("/coagulation/rl")
def predict_coagulation_rl(data: CoagulationRLInput):
    try:
        payload = data.dict()
        input_timestamp = payload.pop("input_timestamp", None)
        data_status = payload.pop("data_status", None)
        maintenance_active = payload.pop("maintenance_active", False)
        recommendation_timestamp = datetime.now(timezone.utc).isoformat()
        result = get_dosage_suggestion(
            payload,
            input_timestamp=input_timestamp or recommendation_timestamp,
            data_status=data_status,
            maintenance_active=maintenance_active,
        )
        return _persist_advisory(
            result,
            source="manual",
            timestamp=recommendation_timestamp,
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
        timestamp = latest_mock_pims_input.pop("timestamp")

        result = get_dosage_suggestion(
            latest_mock_pims_input,
            input_timestamp=timestamp,
        )
        return _persist_advisory(result, source="mock_pims", timestamp=timestamp)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class OperatorDecision(BaseModel):
    decision: Literal["accepted", "rejected"]


def _recommendation_history(limit: int = 200) -> list[dict]:
    items = observation_history("fecl3_dose_recommendation", limit=limit)
    decisions = {}
    for item in items:
        if item.get("kind") == "operator_decision":
            metadata = item.get("metadata", {})
            decisions[str(metadata.get("recommendation_id"))] = {
                "operator_decision": metadata.get("decision"),
                "operator_decision_timestamp": item.get("observed_at"),
            }

    history = []
    for item in items:
        if item.get("kind") != "prediction":
            continue
        metadata = item.get("metadata", {})
        decision = decisions.get(str(item.get("id")), {})
        history.append(
            {
                "recommendation_id": item.get("id"),
                "recommendation_timestamp": item.get("observed_at"),
                "input_data_timestamp": metadata.get("input_data_timestamp"),
                "current_actual_dose": metadata.get("current_actual_dose"),
                "recommended_dose": metadata.get("recommended_dose", item.get("value")),
                "dose_unit": metadata.get("dose_unit", item.get("unit")),
                "predicted_turbidity_current_dose": metadata.get(
                    "predicted_turbidity_current_dose"
                ),
                "predicted_turbidity_recommended_dose": metadata.get(
                    "predicted_turbidity_recommended_dose"
                ),
                "operator_decision": decision.get("operator_decision", "pending"),
                "operator_decision_timestamp": decision.get(
                    "operator_decision_timestamp"
                ),
                "model_name": metadata.get("model_name"),
                "model_version": metadata.get("model_version", item.get("model_version")),
                "model_training_date": metadata.get("model_training_date"),
                "data_quality_status": metadata.get("data_quality_status"),
            }
        )
    return history


@router.get("/coagulation/rl/history")
def get_coagulation_rl_history(limit: int = Query(200, ge=1, le=2000)):
    items = _recommendation_history(limit)
    return {"items": items, "count": len(items)}


@router.post("/coagulation/rl/recommendations/{recommendation_id}/decision")
def record_operator_decision(recommendation_id: str, body: OperatorDecision):
    recommendations = {
        str(item["recommendation_id"]): item for item in _recommendation_history(2000)
    }
    if recommendation_id not in recommendations:
        raise HTTPException(status_code=404, detail="RL recommendation not found")
    recommendation = recommendations[recommendation_id]
    timestamp = datetime.now(timezone.utc).isoformat()
    storage = record_observation(
        sensor_id="fecl3_dose_recommendation",
        value=1.0 if body.decision == "accepted" else 0.0,
        unit="operator decision",
        observed_at=timestamp,
        source="operator",
        model_version=recommendation.get("model_version"),
        kind="operator_decision",
        metadata={
            "recommendation_id": recommendation_id,
            "decision": body.decision,
            "does_not_actuate_dosing": True,
        },
    )
    return {
        "recommendation_id": recommendation_id,
        "operator_decision": body.decision,
        "operator_decision_timestamp": timestamp,
        "dosing_command_sent": False,
        "persistence": storage,
    }


@router.get("/coagulation/rl/history.csv")
def download_coagulation_rl_history_csv(
    limit: int = Query(2000, ge=1, le=2000),
):
    rows = _recommendation_history(limit)
    fields = [
        "recommendation_timestamp",
        "input_data_timestamp",
        "current_actual_dose",
        "recommended_dose",
        "dose_unit",
        "predicted_turbidity_current_dose",
        "predicted_turbidity_recommended_dose",
        "operator_decision",
        "operator_decision_timestamp",
        "model_name",
        "model_version",
        "model_training_date",
        "data_quality_status",
    ]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        stream.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="rl5-recommendation-history.csv"'
        },
    )
