"""Temperature-dependent CT reference used by the CT UI and risk assessment.

The tables and selected log targets reproduce the calculation supplied by the
project supervisor.  The operational reference is the most demanding (largest)
of the Giardia, virus, and E. coli values at the current water temperature.
"""

from __future__ import annotations


TEMPERATURES = (1.0, 5.0, 10.0, 15.0, 20.0, 25.0)
TARGET_LOGS = {"giardia": 1.5, "virus": 1.8, "e_coli": 2.1}

CT_TABLES = {
    "virus": {
        0.5: {1: 0.23, 5: 0.15, 10: 0.13, 15: 0.08, 20: 0.06, 25: 0.04},
        1.0: {1: 0.46, 5: 0.30, 10: 0.26, 15: 0.16, 20: 0.13, 25: 0.08},
        1.5: {1: 0.68, 5: 0.45, 10: 0.38, 15: 0.23, 20: 0.19, 25: 0.12},
        2.0: {1: 0.90, 5: 0.60, 10: 0.50, 15: 0.30, 20: 0.25, 25: 0.15},
        2.5: {1: 1.40, 5: 0.90, 10: 0.80, 15: 0.50, 20: 0.40, 25: 0.25},
        3.0: {1: 1.80, 5: 1.20, 10: 1.00, 15: 0.60, 20: 0.50, 25: 0.30},
    },
    "giardia": {
        0.5: {1: 0.48, 5: 0.32, 10: 0.23, 15: 0.16, 20: 0.12, 25: 0.08},
        1.0: {1: 0.97, 5: 0.63, 10: 0.48, 15: 0.32, 20: 0.24, 25: 0.16},
        1.5: {1: 1.50, 5: 0.95, 10: 0.72, 15: 0.48, 20: 0.36, 25: 0.24},
        2.0: {1: 1.90, 5: 1.30, 10: 0.95, 15: 0.63, 20: 0.48, 25: 0.32},
        2.5: {1: 2.40, 5: 1.60, 10: 1.20, 15: 0.79, 20: 0.60, 25: 0.40},
        3.0: {1: 2.90, 5: 1.90, 10: 1.40, 15: 0.95, 20: 0.72, 25: 0.48},
    },
    "e_coli": {
        0.5: {1: 0.24, 5: 0.16, 10: 0.12, 15: 0.08, 20: 0.06, 25: 0.04},
        1.0: {1: 0.49, 5: 0.32, 10: 0.24, 15: 0.16, 20: 0.12, 25: 0.08},
        1.5: {1: 0.75, 5: 0.48, 10: 0.36, 15: 0.24, 20: 0.18, 25: 0.12},
        2.0: {1: 0.95, 5: 0.65, 10: 0.48, 15: 0.32, 20: 0.24, 25: 0.16},
        2.5: {1: 1.20, 5: 0.80, 10: 0.60, 15: 0.40, 20: 0.30, 25: 0.20},
        3.0: {1: 1.45, 5: 0.95, 10: 0.70, 15: 0.48, 20: 0.36, 25: 0.24},
    },
}


def _interpolate(y1: float, y2: float, x1: float, x2: float, x: float) -> float:
    if x1 == x2:
        return y1
    return y1 + (x - x1) * (y2 - y1) / (x2 - x1)


def _table_value(table: dict, log_target: float, temperature: float) -> float:
    logs = sorted(table)
    bounded_log = max(min(float(log_target), logs[-1]), logs[0])
    lower_log = max(value for value in logs if value <= bounded_log)
    upper_log = min(value for value in logs if value >= bounded_log)
    lower_temp = max(value for value in TEMPERATURES if value <= temperature)
    upper_temp = min(value for value in TEMPERATURES if value >= temperature)

    at_lower_log = _interpolate(
        table[lower_log][lower_temp], table[lower_log][upper_temp],
        lower_temp, upper_temp, temperature,
    )
    at_upper_log = _interpolate(
        table[upper_log][lower_temp], table[upper_log][upper_temp],
        lower_temp, upper_temp, temperature,
    )
    return _interpolate(
        at_lower_log, at_upper_log, lower_log, upper_log, bounded_log
    )


def calculate_ct_reference(water_temperature: float) -> dict:
    """Return the supervisor-aligned strictest CT target at this temperature."""
    bounded_temperature = max(1.0, min(25.0, float(water_temperature)))
    requirements = {
        organism: _table_value(
            CT_TABLES[organism], TARGET_LOGS[organism], bounded_temperature
        )
        for organism in ("giardia", "virus", "e_coli")
    }
    governing_organism = max(requirements, key=requirements.get)
    return {
        "water_temperature_c": round(float(water_temperature), 3),
        "calculation_temperature_c": round(bounded_temperature, 3),
        "temperature_was_bounded": bounded_temperature != float(water_temperature),
        "required_ct": round(requirements[governing_organism], 3),
        "governing_organism": governing_organism,
        "target_log_removal": TARGET_LOGS[governing_organism],
        "requirements": {
            organism: {
                "target_log_removal": TARGET_LOGS[organism],
                "required_ct": round(value, 3),
            }
            for organism, value in requirements.items()
        },
        "unit": "mg O3*min/L",
        "method": "supervisor_temperature_interpolation",
    }
