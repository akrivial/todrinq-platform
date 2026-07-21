from datetime import datetime, timezone

from app.services.observation_store import (
    claim_scheduler_slot,
    database_status,
    finish_scheduler_slot,
    observation_history,
    record_observation,
)


def test_sqlite_observation_roundtrip():
    sensor_id = "test_aws_persistence"
    timestamp = datetime.now(timezone.utc).isoformat()
    stored = record_observation(
        sensor_id=sensor_id, value=1.25, unit="test", observed_at=timestamp,
        source="automated_test", model_version="test", metadata={"input": 7},
    )
    items = observation_history(sensor_id, limit=1)
    assert stored["storage"] in {"sqlite", "postgresql"}
    assert items[-1]["value"] == 1.25
    assert items[-1]["metadata"]["input"] == 7
    assert database_status()["ok"] is True


def test_scheduler_slot_is_unique():
    slot = datetime.now(timezone.utc).replace(microsecond=0)
    job = f"test-slot-{slot.timestamp()}"
    assert claim_scheduler_slot(job, slot) is True
    assert claim_scheduler_slot(job, slot) is False
    finish_scheduler_slot(job, slot, "completed", {"ok": True})
