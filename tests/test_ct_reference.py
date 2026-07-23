import pytest

from app.services.ct_reference import calculate_ct_reference


@pytest.mark.parametrize(
    ("temperature", "expected"),
    [
        (1.0, 1.500),
        (5.0, 0.950),
        (10.0, 0.720),
        (15.0, 0.480),
        (20.0, 0.360),
        (25.0, 0.240),
    ],
)
def test_strictest_supervisor_target_is_selected_at_table_temperatures(
    temperature, expected
):
    result = calculate_ct_reference(temperature)
    assert result["required_ct"] == pytest.approx(expected)
    assert result["governing_organism"] == "giardia"
    assert result["target_log_removal"] == 1.5


def test_reference_interpolates_between_temperatures():
    result = calculate_ct_reference(7.5)
    assert result["required_ct"] == pytest.approx(0.835)
    assert result["requirements"]["giardia"]["required_ct"] == pytest.approx(0.835)


def test_reference_bounds_temperature_to_supervisor_table_range():
    below = calculate_ct_reference(-2)
    above = calculate_ct_reference(30)
    assert below["calculation_temperature_c"] == 1.0
    assert below["required_ct"] == pytest.approx(1.5)
    assert below["temperature_was_bounded"] is True
    assert above["calculation_temperature_c"] == 25.0
    assert above["required_ct"] == pytest.approx(0.24)
    assert above["temperature_was_bounded"] is True
