from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.routes import coagulation_rl as rl_route
from app.routes import rws_test
from app.services.coagulation_rl import get_dosage_suggestion
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


@pytest.mark.parametrize(
    ("family", "months"),
    [
        ("rl_coagulation", 6),
        ("coagulation_performance", 6),
        ("ct", 12),
        ("bromate", 12),
        ("coliform_removal", 12),
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
    assert result["review_status"] == "model review required"
    assert result["retraining"] == "manual, reviewed, and authorised only"


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
