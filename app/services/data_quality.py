"""Shared data-quality evaluation for operational inputs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping


DATA_QUALITY_STATES = {"valid", "stale", "incomplete", "unavailable", "maintenance"}
WATERNET_STALE_AFTER = timedelta(minutes=10)


def _utc_datetime(value: str | datetime | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def assess_operational_inputs(
    values: Mapping[str, Any],
    required_fields: Iterable[str],
    *,
    observed_at: str | datetime | None,
    now: datetime | None = None,
    stale_after: timedelta = WATERNET_STALE_AFTER,
    declared_status: str | None = None,
    maintenance_active: bool = False,
) -> dict[str, Any]:
    """Return one of the five approved operator-visible data-quality states."""
    required_fields = tuple(required_fields)
    now_utc = _utc_datetime(now) or datetime.now(timezone.utc)
    timestamp = _utc_datetime(observed_at)
    missing = [name for name in required_fields if values.get(name) is None]

    if maintenance_active or declared_status == "maintenance":
        status = "maintenance"
        reason = "The operational data source is under maintenance."
    elif declared_status == "unavailable":
        status = "unavailable"
        reason = "No usable operational input values are available."
    elif missing:
        status = "incomplete" if len(missing) < len(required_fields) else "unavailable"
        reason = "Missing required input values: " + ", ".join(missing) + "."
    elif declared_status in {"stale", "incomplete"}:
        status = declared_status
        reason = (
            "One or more required input values are stale."
            if status == "stale"
            else "One or more required input values are incomplete."
        )
    elif timestamp is not None and now_utc - timestamp > stale_after:
        status = "stale"
        reason = (
            f"Required Waternet PIMS/SCADA input is older than "
            f"{int(stale_after.total_seconds() // 60)} minutes."
        )
    else:
        status = "valid"
        reason = "All required operational inputs are present and within the accepted recency limit."

    age_seconds = max(0.0, (now_utc - timestamp).total_seconds()) if timestamp else None
    return {
        "status": status,
        "valid": status == "valid",
        "reason": reason,
        "observed_at": timestamp.isoformat() if timestamp else None,
        "age_seconds": age_seconds,
        "stale_after_seconds": stale_after.total_seconds(),
        "missing_fields": missing,
    }
