"""Manual model-review metadata; this module never retrains models."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
import json
import os


REVIEW_THRESHOLDS_MONTHS = {
    "source_turbidity": 6,
    "rl_coagulation": 6,
    "coagulation_performance": 6,
    "ct": 6,
    "bromate": 6,
    "coliform_removal": 6,
}
CRITICAL_REVIEW_MONTHS = 12

# File-level GitHub provenance for the artefacts deployed by this platform.
# Private-repository dates are approximate values taken from GitHub's relative-age display.
ARTEFACT_COMMITS = {
    "source_turbidity": {
        "date": "2026-05-21", "sha": "9d4e3f5", "precision": "exact",
        "repository": "GregKyri/TODRINQ-Turbidity_inlet_model",
    },
    "coagulation_performance": {
        "date": "2026-05-18", "sha": "521f629", "precision": "approximate",
        "repository": "ToDrinQ_hybrid_model",
    },
    "rl_coagulation": {
        "date": "2026-07-28", "sha": "b58a1e6", "precision": "approximate",
        "repository": "RL_coaggulation_TODRINQ",
    },
    "ct": {
        "date": "2026-04-16", "sha": "8053f58", "precision": "exact",
        "repository": "GregKyri/TODRINQ-Ozonation_model",
    },
    "bromate": {
        "date": "2026-07-21", "sha": "da0d8ba", "precision": "exact",
        "repository": "GregKyri/TODRINQ-Ozonation_model",
    },
    "coliform_removal": {
        "date": "2026-03-30", "sha": "e99c6db", "precision": "exact",
        "repository": "GregKyri/TODRINQ-Ozonation_model",
    },
}


def _configured_dates(variable: str) -> dict[str, str]:
    try:
        value = json.loads(os.getenv(variable, "{}"))
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def model_lifecycle(
    *,
    family: str,
    name: str,
    version: str,
    training_date: str | None = None,
    last_review_date: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    threshold = REVIEW_THRESHOLDS_MONTHS.get(family, 6)
    training_date = training_date or _configured_dates("TODRINQ_MODEL_TRAINING_DATES").get(family)
    last_review_date = last_review_date or _configured_dates("TODRINQ_MODEL_REVIEW_DATES").get(family)
    artefact = ARTEFACT_COMMITS.get(family, {})
    artefact_commit_date = artefact.get("date")
    reference_text = last_review_date or training_date or artefact_commit_date
    reference_type = (
        "confirmed review" if last_review_date else
        "confirmed training" if training_date else
        "GitHub artefact commit" if artefact_commit_date else
        "unavailable"
    )
    current = today or datetime.now(timezone.utc).date()
    reference = date.fromisoformat(reference_text) if reference_text else None
    age_days = (current - reference).days if reference else None
    if reference is None:
        status = "pending model-owner metadata"
        level = "pending"
        warning = "Training and review dates are pending confirmation; model age cannot be verified."
    elif age_days > CRITICAL_REVIEW_MONTHS * 30.4375:
        status = "model review overdue"
        level = "overdue"
        warning = (
            f"Model review overdue: the latest {reference_type.lower()} is more than "
            "12 months old. Prioritise expert review and an authorised retraining assessment."
        )
    elif age_days > threshold * 30.4375:
        status = "model review recommended"
        level = "review"
        warning = (
            f"Model review recommended: the latest {reference_type.lower()} is more than "
            "six months old. Assess recent data and performance before deciding whether "
            "authorised retraining is needed."
        )
    else:
        status = "within review interval"
        level = "current"
        warning = (
            f"The latest {reference_type.lower()} is within the six-month review interval. "
            "Continue routine performance monitoring."
        )
    return {
        "model_name": name,
        "model_version": version,
        "training_date": training_date,
        "last_review_date": last_review_date,
        "artefact_commit_date": artefact_commit_date,
        "artefact_commit_sha": artefact.get("sha"),
        "artefact_commit_precision": artefact.get("precision"),
        "artefact_repository": artefact.get("repository"),
        "age_reference_type": reference_type,
        "age_reference_date": reference_text,
        "age_calculated_on": current.isoformat(),
        "model_age_days": age_days,
        "review_threshold_months": threshold,
        "overdue_threshold_months": CRITICAL_REVIEW_MONTHS,
        "review_status": status,
        "review_warning": warning,
        "lifecycle_level": level,
        "prediction_service_available": True,
        "retraining": "manual, reviewed, and authorised only",
    }
