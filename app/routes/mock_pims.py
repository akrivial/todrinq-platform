from fastapi import APIRouter
from datetime import datetime, timezone
import random

router = APIRouter()


def generate_coagulation_data(observed_at: str | None = None):
    return {
        "timestamp": observed_at or datetime.now(timezone.utc).isoformat(),
        "ftu_raw_water": round(random.uniform(3.0, 12.0), 2),
        "fecl3_concentration": round(random.uniform(1.0, 8.0), 2),
        "temperature_raw_water": round(random.uniform(5.0, 22.0), 2),
        "ph_raw_water": round(random.uniform(6.5, 8.5), 2),
        "after_dredging": random.randint(0, 1),
        "lane": random.choice([1, 2, 3]),
        "year": datetime.utcnow().year,
    }


def generate_coagulation_measurement(observed_at: str, expected_turbidity: float | None = None):
    """Mock outlet-turbidity feed; replace its caller with real PIMS later."""
    centre = float(expected_turbidity) if expected_turbidity is not None else random.uniform(0.4, 8.0)
    uncertainty = max(0.08, abs(centre) * 0.08)
    return {
        "timestamp": observed_at,
        "outlet_turbidity": round(max(0.0, centre + random.gauss(0.0, uncertainty)), 3),
        "unit": "NTU / model output",
        "source": "mock_pims_coagulation_measurement",
        "quality": "synthetic_demo",
    }


def generate_ct_data(observed_at: str | None = None):
    return {
        "timestamp": observed_at or datetime.now(timezone.utc).isoformat(),
        "Chamber": round(random.uniform(1, 4), 2),
        "WaterTemperature": round(random.uniform(5.0, 22.0), 2),
        "RFTurbidity": round(random.uniform(0.1, 5.0), 2),
        "FlowRate": round(random.uniform(100.0, 500.0), 2),
        "Ozonedosage": round(random.uniform(0.5, 5.0), 2),
    }


def generate_ct_measurement(observed_at: str, expected_ct: float | None = None):
    """Mock the sparse CT result feed that will later be replaced by real PIMS/lab data.

    ``observed_at`` is supplied by the sampling schedule so the measurement and
    its corresponding model prediction refer to exactly the same sample time.
    ``expected_ct`` keeps demonstration values plausible; it is not returned as
    or labelled as a real Waternet measurement.
    """
    centre = float(expected_ct) if expected_ct is not None else random.uniform(0.7, 1.6)
    uncertainty = max(0.03, abs(centre) * 0.06)
    return {
        "timestamp": observed_at,
        "CT_All": round(max(0.0, centre + random.gauss(0.0, uncertainty)), 4),
        "unit": "mg*min/L",
        "source": "mock_pims_ct_measurement",
        "quality": "synthetic_demo",
    }


def generate_bromate_data():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "month": datetime.utcnow().month,
        "Chamber": round(random.uniform(1, 4), 2),
        "WaterTemperature": round(random.uniform(5.0, 22.0), 2),
        "RFTurbidity": round(random.uniform(0.1, 5.0), 2),
        "FlowRate": round(random.uniform(100.0, 500.0), 2),
        "Ozonedosage": round(random.uniform(0.5, 5.0), 2),
        "Residencetime": round(random.uniform(1.0, 30.0), 2),
        "WaterTemperature_1": round(random.uniform(5.0, 22.0), 2),
        "RFturbidity_1": round(random.uniform(0.1, 5.0), 2),
        "FlowRate_1": round(random.uniform(100.0, 500.0), 2),
        "Ozonedosage_1": round(random.uniform(0.5, 5.0), 2),
        "CT_All": round(random.uniform(5.0, 40.0), 2),
    }


def generate_coliform_data():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "Chamber": round(random.uniform(1, 4), 2),
        "WaterTemperature": round(random.uniform(5.0, 22.0), 2),
        "RFTurbidity": round(random.uniform(0.1, 5.0), 2),
        "FlowRate": round(random.uniform(100.0, 500.0), 2),
        "Ozonedosage": round(random.uniform(0.5, 5.0), 2),
        "RFturbidity_1": round(random.uniform(0.1, 5.0), 2),
        "CT_All": round(random.uniform(5.0, 40.0), 2),
    }


@router.get("/coagulation/latest", summary="Get latest mock coagulation input")
def get_latest_coagulation():
    return generate_coagulation_data()


@router.get("/ct/latest", summary="Get latest mock CT input")
def get_latest_ct():
    return generate_ct_data()


@router.get("/bromate/latest", summary="Get latest mock bromate input")
def get_latest_bromate():
    return generate_bromate_data()


@router.get("/coliform/latest", summary="Get latest mock coliform input")
def get_latest_coliform():
    return generate_coliform_data()


def generate_sose9_data():
    """
    Generate mock PIMS input data for SoSe #9.

    The trained soft-sensor model is still responsible for the prediction; this
    function only creates plausible synthetic inputs for demo mode.

    Turbidity is constrained to realistic source-water demo values:
      - Normal: typical 5-15 FTU
      - Warning: occasional 15-30 FTU
      - Extreme event: explicit storm/flood scenario above 30 FTU

    Lag convention: lag1 is the most recent previous hour and lag24 is 24h ago.
    """
    month = datetime.utcnow().month
    scenario = random.choices(
        ["normal", "typical_high", "warning", "extreme_event"],
        weights=[72, 22, 5, 1],
    )[0]

    # Rhine/Lek system: Hag_dis training range was -42 to 1380 m³/s
    # Turbidity training range: 3.65 to 167 FTU (raw inlet, before treatment)
    if scenario == "normal":
        current_turb = round(random.uniform(5.0, 10.0), 2)
        start_turb   = round(current_turb + random.uniform(-0.8, 0.8), 2)
        current_hag  = round(random.uniform(40.0, 120.0), 1)
        start_hag    = round(current_hag + random.uniform(-12.0, 12.0), 1)
        temp         = round(random.uniform(13.0, 21.0), 1)
    elif scenario == "typical_high":
        current_turb = round(random.uniform(10.0, 16.0), 2)
        start_turb   = round(current_turb + random.uniform(-1.5, 0.5), 2)
        current_hag  = round(random.uniform(90.0, 220.0), 1)
        start_hag    = round(current_hag + random.uniform(-20.0, 10.0), 1)
        temp         = round(random.uniform(10.0, 18.0), 1)
    elif scenario == "warning":
        current_turb = round(random.uniform(18.0, 24.0), 2)
        start_turb   = round(current_turb + random.uniform(-2.0, 0.0), 2)
        current_hag  = round(random.uniform(160.0, 320.0), 1)
        start_hag    = round(current_hag + random.uniform(-30.0, 5.0), 1)
        temp         = round(random.uniform(8.0, 15.0), 1)
    else:  # extreme_event
        current_turb = round(random.uniform(30.0, 60.0), 2)
        start_turb   = round(random.uniform(10.0, 25.0), 2)
        current_hag  = round(random.uniform(550.0, 950.0), 1)
        start_hag    = round(current_hag * random.uniform(0.35, 0.65), 1)
        temp         = round(random.uniform(3.5, 10.0), 1)

    def ramp(start, end, n=24, noise=0.05, min_value=None, max_value=None, max_step=None):
        """Return lag1..lag24, where lag1 is nearest to the current value."""
        oldest_to_newest = [
            round(start + (end - start) * i / (n - 1) + random.uniform(-abs(end - start) * noise, abs(end - start) * noise), 2)
            for i in range(n)
        ]
        if min_value is not None or max_value is not None:
            oldest_to_newest = [
                round(min(max(v, min_value if min_value is not None else v), max_value if max_value is not None else v), 2)
                for v in oldest_to_newest
            ]
        if max_step is not None:
            smoothed = [oldest_to_newest[0]]
            for value in oldest_to_newest[1:]:
                previous = smoothed[-1]
                delta = max(min(value - previous, max_step), -max_step)
                smoothed.append(round(previous + delta, 2))
            oldest_to_newest = smoothed
            oldest_to_newest[-1] = round(end, 2)
        return list(reversed(oldest_to_newest))

    turbidity_lag_max = 60.0 if scenario == "extreme_event" else 24.0
    turbidity_max_step = None if scenario == "extreme_event" else 0.25
    discharge_max_step = None if scenario == "extreme_event" else 5.0

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "scenario": scenario,
        "sensor_turbidity": current_turb,
        "Hag_dis": current_hag,
        "sensor_temperature": temp,
        "month": month,
        "sensor_turbidity_lags": ramp(
            start_turb,
            current_turb,
            min_value=3.65,
            max_value=turbidity_lag_max,
            max_step=turbidity_max_step,
        ),
        "Hag_dis_lags": ramp(start_hag, current_hag, max_step=discharge_max_step),
        "sensor_temperature_lags": [round(temp + random.uniform(-0.3, 0.3), 1) for _ in range(24)],
        "month_lags": [month] * 24,
    }


@router.get("/sose9/latest", summary="Get latest mock SoSe #9 input")
def get_latest_sose9():
    return generate_sose9_data()


@router.get("/overview", summary="Get all latest mock PIMS streams")
def get_mock_pims_overview():
    return {
        "coagulation": generate_coagulation_data(),
        "ct": generate_ct_data(),
        "bromate": generate_bromate_data(),
        "coliform": generate_coliform_data(),
        "sose9": generate_sose9_data(),
    }
