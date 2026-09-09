from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.coagulation_domain import FECL3_ACTIONS_MG_L, FECL3_MAX_MG_L, FECL3_MIN_MG_L
from app.routes import coagulation_rl as rl_route
from app.routes.mock_pims import generate_coagulation_data
from app.routes import rws_test
from app.services.coagulation_rl import (
    ACTION_MAP,
    _select_lower_dose_improvement,
    get_dosage_suggestion,
)
from app.services.data_quality import assess_operational_inputs
from app.services.model_lifecycle import model_lifecycle


VALID_INPUT = {
    "ftu_raw_water": 15.2,
    "fecl3_concentration": 5.0,
    "temperature_raw_water": 16.0,
    "ph_raw_water": 7.4,
    "after_dredging": 450.0,
    "lane": 1,
    "year": 2026,
    "flow_coagulation_1": 1000.0,
}


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, "valid"),
        ({"observed_at": datetime.now(timezone.utc) - timedelta(minutes=11)}, "stale"),
        ({"values": {**VALID_INPUT, "ph_raw_water": None}}, "incomplete"),
        ({"declared_status": "unavailable"}, "unavailable"),
        ({"maintenance_active": True}, "maintenance"),
    ],
)
def test_approved_data_quality_states(overrides, expected):
    args = {
        "values": VALID_INPUT,
        "required_fields": (
            "ftu_raw_water",
            "fecl3_concentration",
            "temperature_raw_water",
            "ph_raw_water",
            "after_dredging",
            "lane",
            "year",
        ),
        "observed_at": datetime.now(timezone.utc),
    }
    args.update(overrides)
    assert assess_operational_inputs(**args)["status"] == expected


@pytest.mark.parametrize(
    "kwargs",
    [
        {"input_timestamp": (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat()},
        {"data_status": "unavailable"},
        {"maintenance_active": True},
    ],
)
def test_invalid_operational_data_suppresses_rl_advice(kwargs):
    result = get_dosage_suggestion(VALID_INPUT, **kwargs)
    assert result["recommendation_available"] is False
    assert result["recommended_fecl3_concentration"]["value"] is None
    assert result["predicted_turbidity_recommended_dose"]["value"] is None


def test_missing_required_input_suppresses_rl_advice():
    result = get_dosage_suggestion(
        {**VALID_INPUT, "ph_raw_water": None},
        input_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    assert result["data_quality"]["status"] == "incomplete"
    assert result["recommendation_available"] is False


def test_valid_recent_input_returns_four_separate_rl_values():
    result = get_dosage_suggestion(
        VALID_INPUT,
        input_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    assert result["recommendation_available"] is True
    assert result["current_fecl3_dose"]["value"] == 5.0
    assert result["recommended_fecl3_concentration"]["value"] is not None
    assert result["predicted_turbidity_current_dose"]["value"] is not None
    assert result["predicted_turbidity_recommended_dose"]["value"] is not None


def test_mock_pims_fecl3_stays_inside_validated_rl_domain():
    for _ in range(1000):
        dose = generate_coagulation_data()["fecl3_concentration"]
        assert FECL3_MIN_MG_L <= dose <= FECL3_MAX_MG_L


@pytest.mark.parametrize("dose", [1.49, 6.01])
def test_rl_api_rejects_fecl3_outside_validated_domain(dose):
    with pytest.raises(ValidationError):
        rl_route.CoagulationRLInput(fecl3_concentration=dose)


@pytest.mark.parametrize("dose", [FECL3_MIN_MG_L, FECL3_MAX_MG_L])
def test_rl_api_accepts_fecl3_domain_boundaries(dose):
    body = rl_route.CoagulationRLInput(fecl3_concentration=dose)
    assert body.fecl3_concentration == dose


def test_rl_action_map_matches_shared_validated_domain():
    assert tuple(ACTION_MAP) == FECL3_ACTIONS_MG_L


def test_service_withholds_advice_for_out_of_domain_current_dose():
    result = get_dosage_suggestion(
        {**VALID_INPUT, "fecl3_concentration": 6.01},
        input_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    assert result["data_quality"]["status"] == "out_of_domain"
    assert result["recommendation_available"] is False
    assert result["recommended_fecl3_concentration"]["value"] is None


class _DoseResponseModel:
    def __init__(self, predictions):
        self.predictions = predictions

    def predict(self, frame, verbose=0):
        dose = float(frame.iloc[0]["fecl3_concentration"])
        return [[self.predictions[dose]]]


def test_rl_safety_filter_selects_highest_q_lower_dose_with_lower_turbidity():
    q_values = [0.1, 0.9, 0.8, 0.2, 0.0, -0.1, -0.2, -0.3]
    selected = _select_lower_dose_improvement(
        model_input={**VALID_INPUT, "fecl3_concentration": 2.75},
        current_prediction=5.99,
        q_values=q_values,
        supervised_model=_DoseResponseModel({1.5: 5.70, 2.0: 5.86, 2.5: 6.10}),
    )
    assert selected[:3] == (1, 2.0, 5.86)


def test_rl_safety_filter_withholds_when_lower_dose_does_not_improve_turbidity():
    selected = _select_lower_dose_improvement(
        model_input={**VALID_INPUT, "fecl3_concentration": 2.75},
        current_prediction=5.99,
        q_values=[0.1, 0.9, 0.8, 0.2, 0.0, -0.1, -0.2, -0.3],
        supervised_model=_DoseResponseModel({1.5: 6.20, 2.0: 6.10, 2.5: 6.01}),
    )
    assert selected[0] is None


@pytest.mark.parametrize(
    ("family", "months"),
    [
        ("source_turbidity", 6),
        ("rl_coagulation", 6),
        ("coagulation_performance", 6),
        ("ct", 6),
        ("bromate", 6),
        ("coliform_removal", 6),
    ],
)
def test_model_review_thresholds(family, months):
    result = model_lifecycle(
        family=family,
        name="test",
        version="test",
        last_review_date="2024-01-01",
        today=date(2026, 7, 30),
    )
    assert result["review_threshold_months"] == months
    assert result["review_status"] == "model review overdue"
    assert result["lifecycle_level"] == "overdue"
    assert result["retraining"] == "manual, reviewed, and authorised only"


@pytest.mark.parametrize(
    ("last_review_date", "expected_level"),
    [
        ("2026-04-01", "current"),
        ("2025-11-01", "review"),
        ("2025-01-01", "overdue"),
    ],
)
def test_model_lifecycle_colour_boundaries(last_review_date, expected_level):
    result = model_lifecycle(
        family="coagulation_performance",
        name="test",
        version="test",
        last_review_date=last_review_date,
        today=date(2026, 7, 30),
    )
    assert result["lifecycle_level"] == expected_level
    assert result["prediction_service_available"] is True


@pytest.mark.parametrize(
    ("family", "expected_date", "expected_days", "precision"),
    [
        ("source_turbidity", "2026-05-21", 89, "exact"),
        ("coagulation_performance", "2026-05-18", 92, "approximate"),
        ("rl_coagulation", "2026-07-28", 21, "approximate"),
        ("ct", "2026-04-16", 124, "exact"),
        ("bromate", "2026-07-21", 28, "exact"),
        ("coliform_removal", "2026-03-30", 141, "exact"),
    ],
)
def test_github_artefact_reference_ages(family, expected_date, expected_days, precision):
    result = model_lifecycle(
        family=family, name="test", version="test", today=date(2026, 8, 18)
    )
    assert result["artefact_commit_date"] == expected_date
    assert result["artefact_commit_precision"] == precision
    assert result["age_reference_type"] == "GitHub artefact commit"
    assert result["model_age_days"] == expected_days
    assert result["age_calculated_on"] == "2026-08-18"
    assert result["lifecycle_level"] == "current"
    assert result["training_date"] is None


def test_rws_failure_preserves_original_api_error_response(monkeypatch):
    monkeypatch.setattr(
        rws_test,
        "fetch_rws_observations",
        lambda **_: {
            "status_code": None,
            "connection_error": "network down",
        },
    )
    result = rws_test.get_latest_rws_value(
        location="hagestein_boven",
        parameter="water_temperature",
    )
    assert result["message"] == "RWS API request failed"
    assert result["details"]["connection_error"] == "network down"
    assert "latest_value" not in result


def test_rws_no_content_is_reported_as_no_data(monkeypatch):
    monkeypatch.setattr(
        rws_test,
        "fetch_rws_observations",
        lambda **_: {
            "status_code": 204,
            "response": {"raw_text": ""},
        },
    )
    latest = rws_test.get_latest_rws_value(
        location="hagestein_boven",
        parameter="water_temperature",
    )
    series = rws_test.get_rws_timeseries(
        location="hagestein_boven",
        parameter="water_temperature",
        days_back=2,
    )
    assert latest["status"] == "no_data"
    assert series["status"] == "no_data"
    assert series["count"] == 0
    assert series["timeseries"] == []


def test_operator_decision_records_no_dosing_command(monkeypatch):
    monkeypatch.setattr(
        rl_route,
        "_recommendation_history",
        lambda limit=200: [{"recommendation_id": 42, "model_version": "candidate"}],
    )
    monkeypatch.setattr(
        rl_route,
        "record_observation",
        lambda **kwargs: {"id": 99, "storage": "test"},
    )
    result = rl_route.record_operator_decision(
        "42", rl_route.OperatorDecision(decision="accepted")
    )
    assert result["operator_decision"] == "accepted"
    assert result["dosing_command_sent"] is False


def test_csv_keeps_actual_and_recommended_doses_separate(monkeypatch):
    monkeypatch.setattr(
        rl_route,
        "_recommendation_history",
        lambda limit=2000: [
            {
                "recommendation_timestamp": "2026-07-30T00:00:00+00:00",
                "current_actual_dose": 5.0,
                "recommended_dose": 3.5,
            }
        ],
    )
    response = rl_route.download_coagulation_rl_history_csv()
    csv_text = response.body.decode()
    assert "current_actual_dose,recommended_dose" in csv_text
    assert "5.0,3.5" in csv_text


def test_ui_has_one_navigation_row_and_four_rl_values():
    html = (
        Path(__file__).parents[1] / "app" / "static" / "ui" / "index.html"
    ).read_text(encoding="utf-8")
    assert html.count('class="architecture-row"') == 1
    assert 'class="home-module-card" data-nav=' not in html
    assert 'id="rl5-current-dose-display"' in html
    assert 'id="rl5-recommended-dose-display"' in html
    assert 'id="rl5-current-turbidity-display"' in html
    assert 'id="rl5-recommended-turbidity-display"' in html
    assert 'id="btn-rl5-accept"' in html
    assert 'id="btn-rl5-reject"' in html


def test_coagulation_history_ui_describes_six_hour_forecast_matching():
    root = Path(__file__).parents[1]
    html = (root / "app" / "static" / "ui" / "index.html").read_text(encoding="utf-8")
    javascript = (root / "app" / "static" / "ui" / "app.js").read_text(encoding="utf-8")
    assert "six completed +6h forecasts" in html.lower()
    assert "issued six hours before its target time" in html.lower()
    assert 'id="coagulation-now-time"' in html
    assert 'id="coagulation-target-time"' in html
    assert 'id="coagulation-future-prediction"' in html
    assert 'Number(item.metadata.forecast_horizon_hours) === 6' in javascript
    assert '"NOW"' in javascript[javascript.index("function renderCoagulationStoredHistory"):javascript.index("async function loadCoagulationDatabaseHistory")]
