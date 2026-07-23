import math

from app.routes.mock_pims import generate_coliform_data
from app.services import ozonation_predictions


def test_coliform_prediction_converts_holm_coefficient_to_positive_log_reduction(monkeypatch):
    monkeypatch.setattr(
        ozonation_predictions,
        "_predict_from_list",
        lambda model_key, values: 0.02,
    )
    values = [[2, 12.0, 0.14, 2000.0, 0.75, 0.14, 0.65]]

    result = ozonation_predictions.predict_coliform(values)

    residence_time = 573.86 * 60.0 / 2000.0
    ozone_logmean = (0.75 - 0.012) / math.log10(0.75 / 0.012)
    assert result == 0.02 * ozone_logmean * residence_time**2
    assert result > 0


def test_mock_coliform_inputs_follow_delivered_scaler_domain():
    sample = generate_coliform_data()

    assert sample["Chamber"] in {1, 2, 3, 4}
    assert 0.04 <= sample["RFTurbidity"] <= 0.30
    assert 1750.0 <= sample["FlowRate"] <= 2350.0
    assert 0.55 <= sample["Ozonedosage"] <= 0.95
    assert 0.15 <= sample["CT_All"] <= 1.30
