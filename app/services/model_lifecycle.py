"""Manual model-review metadata; this module never retrains models."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any


REVIEW_THRESHOLDS_MONTHS = {
    "rl_coagulation": 6,
    "coagulation_performance": 6,
    "ct": 12,
    "bromate": 12,
    "coliform_removal": 12,
}


def model_lifecycle(
    *,
    family: str,
    name: str,
    version: str,
    training_date: str | None = None,
    last_review_date: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    threshold = REVIEW_THRESHOLDS_MONTHS.get(family)
    reference_text = last_review_date or training_date
    current = today or datetime.now(timezone.utc).date()
    reference = date.fromisoformat(reference_text) if reference_text else None
    age_days = (current - reference).days if reference else None
    review_required = bool(
        threshold is not None and age_days is not None and age_days > threshold * 30.4375
    )
    if reference is None:
        status = "pending model-owner metadata"
        warning = "Training and review dates are pending confirmation; model age cannot be verified."
    elif review_required:
        status = "model review required"
        period = "six" if threshold == 6 else "twelve"
        warning = (
            "Model review required: this model has not been reviewed or retrained "
            f"within the previous {period} months."
        )
    else:
        status = "within review interval"
        warning = None
    return {
        "model_name": name,
        "model_version": version,
        "training_date": training_date,
        "last_review_date": last_review_date,
        "model_age_days": age_days,
        "review_threshold_months": threshold,
        "review_status": status,
        "review_warning": warning,
        "retraining": "manual, reviewed, and authorised only",
    }
