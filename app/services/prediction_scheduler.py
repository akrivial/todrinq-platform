"""Backend-owned hourly prediction cycle for unattended deployments."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.observation_store import claim_scheduler_slot, finish_scheduler_slot


logger = logging.getLogger("todrinq.scheduler")
JOB_NAME = "hourly-soft-sensor-predictions"
SCHEDULER_ENABLED = os.getenv("TODRINQ_SCHEDULER_ENABLED", "false").lower() in {"1", "true", "yes"}
SCHEDULER_INTERVAL_SECONDS = max(60, int(os.getenv("TODRINQ_SCHEDULER_INTERVAL_SECONDS", "3600")))

_task: asyncio.Task | None = None
_state: dict[str, Any] = {
    "enabled": SCHEDULER_ENABLED,
    "running": False,
    "last_slot": None,
    "last_started_at": None,
    "last_finished_at": None,
    "last_status": "not_started",
    "last_results": {},
}


def _hour_slot(now: datetime | None = None) -> datetime:
    value = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return value.replace(minute=0, second=0, microsecond=0)


def run_prediction_cycle(slot: datetime | None = None) -> dict[str, Any]:
    """Run each available trained soft sensor once and persist its output."""
    scheduled_for = slot or _hour_slot()
    if not claim_scheduler_slot(JOB_NAME, scheduled_for):
        return {"status": "already_completed_or_running", "slot": scheduled_for.isoformat(), "results": {}}

    from app.routes.predict import predict_coagulation_live
    from app.routes.source import sose9_predict_live
    from app.routes.treatment import bromate_latest, coliform_latest, ct_latest

    jobs = {
        "sose9": sose9_predict_live,
        "sose8": predict_coagulation_live,
        "ct": ct_latest,
        "bromate": bromate_latest,
        "microbial_removal": coliform_latest,
    }
    results: dict[str, Any] = {}
    for name, function in jobs.items():
        try:
            response = function()
            prediction = response.get("prediction")
            if isinstance(prediction, dict):
                prediction = next((v for v in prediction.values() if isinstance(v, (int, float))), None)
            results[name] = {"ok": True, "prediction": prediction}
        except Exception as exc:
            logger.exception("Scheduled prediction failed for %s", name)
            results[name] = {"ok": False, "error": str(exc)}

    successful = sum(1 for item in results.values() if item["ok"])
    status = "completed" if successful == len(results) else "partial" if successful else "failed"
    details = {"successful": successful, "total": len(results), "results": results}
    finish_scheduler_slot(JOB_NAME, scheduled_for, status, details)
    return {"status": status, "slot": scheduled_for.isoformat(), **details}


async def _scheduler_loop() -> None:
    _state["running"] = True
    try:
        while True:
            slot = _hour_slot()
            _state.update(last_slot=slot.isoformat(), last_started_at=datetime.now(timezone.utc).isoformat())
            result = await asyncio.to_thread(run_prediction_cycle, slot)
            _state.update(
                last_finished_at=datetime.now(timezone.utc).isoformat(),
                last_status=result["status"],
                last_results=result.get("results", {}),
            )
            next_hour = slot + timedelta(hours=1)
            seconds_to_next_hour = max(1.0, (next_hour - datetime.now(timezone.utc)).total_seconds())
            await asyncio.sleep(min(seconds_to_next_hour, SCHEDULER_INTERVAL_SECONDS))
    except asyncio.CancelledError:
        raise
    finally:
        _state["running"] = False


def start_prediction_scheduler() -> asyncio.Task | None:
    global _task
    if not SCHEDULER_ENABLED or (_task and not _task.done()):
        return _task
    _task = asyncio.create_task(_scheduler_loop(), name=JOB_NAME)
    logger.info("Hourly prediction scheduler started")
    return _task


async def stop_prediction_scheduler() -> None:
    global _task
    if not _task:
        return
    _task.cancel()
    try:
        await _task
    except asyncio.CancelledError:
        pass
    _task = None


def scheduler_status() -> dict[str, Any]:
    return dict(_state)
