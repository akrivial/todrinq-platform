from datetime import datetime, timedelta, timezone

from app.routes.risk import (
    RELIABILITY_HISTORY,
    aggregate_active_components,
    apply_runtime_reliability,
)


def _response(risk_class: str) -> dict:
    return {"overall_risk": {"class": risk_class, "score": 5 if risk_class == "High" else 1}}


def test_high_requires_three_distinct_consecutive_results():
    RELIABILITY_HISTORY["bromate"].clear()
    base = datetime.now(timezone.utc)
    first = apply_runtime_reliability(
        _response("High"), sensor_key="bromate", value=12.0, raw_class="High",
        prediction_timestamp=base.isoformat(),
        reset_history=True,
    )
    second = apply_runtime_reliability(
        _response("High"), sensor_key="bromate", value=12.2, raw_class="High",
        prediction_timestamp=(base + timedelta(seconds=1)).isoformat(),
    )
    third = apply_runtime_reliability(
        _response("High"), sensor_key="bromate", value=12.1, raw_class="High",
        prediction_timestamp=(base + timedelta(seconds=2)).isoformat(),
    )

    assert first["overall_risk"]["class"] == "Moderate"
    assert first["reliability"]["status"] == "awaiting_confirmation"
    assert second["overall_risk"]["class"] == "Moderate"
    assert second["reliability"]["display_count"] == "2/3"
    assert third["overall_risk"]["class"] == "High"
    assert third["reliability"]["display_count"] == "3/3"


def test_same_timestamp_does_not_increment_confirmation_count():
    RELIABILITY_HISTORY["bromate"].clear()
    timestamp = datetime.now(timezone.utc).isoformat()
    apply_runtime_reliability(
        _response("High"), sensor_key="bromate", value=12.0, raw_class="High",
        prediction_timestamp=timestamp,
        reset_history=True,
    )
    repeated = apply_runtime_reliability(
        _response("High"), sensor_key="bromate", value=12.2, raw_class="High",
        prediction_timestamp=timestamp,
    )
    assert repeated["reliability"]["display_count"] == "1/3"
    assert len(RELIABILITY_HISTORY["bromate"]) == 1


def test_normal_result_breaks_high_persistence():
    RELIABILITY_HISTORY["bromate"].clear()
    apply_runtime_reliability(
        _response("High"), sensor_key="bromate", value=12.0, raw_class="High", reset_history=True
    )
    apply_runtime_reliability(
        _response("Low"), sensor_key="bromate", value=4.0, raw_class="Low"
    )
    result = apply_runtime_reliability(
        _response("High"), sensor_key="bromate", value=12.0, raw_class="High"
    )

    assert result["overall_risk"]["class"] == "Moderate"
    assert result["reliability"]["consecutive_high"] == 1


def test_maintenance_is_unavailable_and_excluded():
    result = apply_runtime_reliability(
        _response("High"),
        sensor_key="ct",
        value=0.2,
        raw_class="High",
        maintenance_active=True,
        reset_history=True,
    )

    assert result["overall_risk"]["class"] == "Unavailable"
    assert result["included_in_risk_aggregation"] is False
    assert aggregate_active_components([result]) == {"class": "Unavailable", "score": 0}


def test_stale_result_is_excluded():
    old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    result = apply_runtime_reliability(
        _response("High"),
        sensor_key="distribution",
        value=0.8,
        raw_class="High",
        prediction_timestamp=old_timestamp,
        reset_history=True,
    )

    assert result["reliability"]["status"] == "stale"
    assert result["included_in_risk_aggregation"] is False


def test_out_of_range_result_is_excluded():
    result = apply_runtime_reliability(
        _response("High"),
        sensor_key="distribution",
        value=1.5,
        raw_class="High",
        reset_history=True,
    )

    assert result["reliability"]["status"] == "invalid"
    assert result["included_in_risk_aggregation"] is False
