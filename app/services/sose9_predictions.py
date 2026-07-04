import logging

import pandas as pd


log = logging.getLogger(__name__)


SOSE9_OUTPUT_MIN_FTU = 0.0
SOSE9_OUTPUT_MAX_FTU = 30.0
SOSE9_EXPLICIT_TARGET_SCALER_KEYS = (
    "target_scaler",
    "target",
    "y_scaler",
    "y",
    "sensor_turbidity_target",
    "predicted_3h_turbidity",
)


def _shift_for_horizon(data: dict, horizon_hours: int) -> dict:
    shifted = {}
    for key, value in data.items():
        if "_lag" in key:
            base, current_lag = key.split("_lag")
            new_lag = int(current_lag) + horizon_hours
            shifted[f"{base}_lag{new_lag}"] = value
        else:
            shifted[f"{key}_lag{horizon_hours}"] = value
    return shifted


def _inverse_sose9_output(raw_pred: float, scaler_dict: dict | None) -> tuple[float, dict]:
    """Convert the trained model output back to FTU using the SoSe #9 target scale.

    The persisted scaler dictionary contains input feature scalers. If a dedicated
    target scaler is not present, do not reuse the input sensor_turbidity scaler:
    that maps normal model outputs onto the full historical input range and
    inflates demo predictions.
    """
    debug = {
        "output_scaling_mode": None,
        "output_inverse_scaler": None,
        "raw_model_output_clamped_for_output_scaling": None,
        "legacy_sensor_turbidity_inverse_output": None,
        "ftu_ntu_conversion_factor": 1.0,
    }

    if scaler_dict:
        for key in SOSE9_EXPLICIT_TARGET_SCALER_KEYS:
            scaler = scaler_dict.get(key)
            if scaler is not None and hasattr(scaler, "inverse_transform"):
                value = float(scaler.inverse_transform([[raw_pred]])[0][0])
                debug["output_scaling_mode"] = "explicit_target_scaler"
                debug["output_inverse_scaler"] = key
                return value, debug

        sensor_scaler = scaler_dict.get("sensor_turbidity")
        if sensor_scaler is not None and hasattr(sensor_scaler, "inverse_transform"):
            debug["legacy_sensor_turbidity_inverse_output"] = float(
                sensor_scaler.inverse_transform([[raw_pred]])[0][0]
            )

    bounded_raw_pred = min(max(raw_pred, 0.0), 1.0)
    debug["raw_model_output_clamped_for_output_scaling"] = bounded_raw_pred
    debug["output_scaling_mode"] = "sose9_operational_output_range"
    debug["output_inverse_scaler"] = "0_to_30_FTU"

    value = SOSE9_OUTPUT_MIN_FTU + bounded_raw_pred * (
        SOSE9_OUTPUT_MAX_FTU - SOSE9_OUTPUT_MIN_FTU
    )
    return float(value), debug


def predict_turbidity_3h(
    model,
    feature_cols: list,
    input_data: dict,
    scaler_dict: dict | None = None,
    return_debug: bool = False,
) -> float:
    """Shift raw inputs by 3h, scale each feature, predict, then inverse-scale output."""
    shifted = _shift_for_horizon(input_data, horizon_hours=3)

    debug = {
        "raw_input_payload": input_data,
        "processed_shifted_input_vector": {col: shifted[col] for col in feature_cols if col in shifted},
        "scaled_input_vector": None,
        "raw_model_output": None,
        "inverse_transformed_output": None,
        "final_predicted_3h_turbidity_FTU": None,
        "scaling": {
            "input_scaling_applied": bool(scaler_dict),
            "output_scaling_mode": None,
            "output_inverse_scaler": None,
            "legacy_sensor_turbidity_inverse_output": None,
            "raw_model_output_clamped_for_output_scaling": None,
            "ftu_ntu_conversion_factor": 1.0,
        },
    }

    if scaler_dict:
        scaled = {
            col: float(scaler_dict[col].transform([[shifted[col]]])[0][0])
            if col in scaler_dict else float(shifted[col])
            for col in feature_cols
        }
        debug["scaled_input_vector"] = scaled
        df = pd.DataFrame([scaled])[feature_cols]
        raw_pred = float(model.predict(df)[0])
        debug["raw_model_output"] = raw_pred
        final_pred, output_scaling_debug = _inverse_sose9_output(raw_pred, scaler_dict)
        debug["scaling"].update(output_scaling_debug)
        debug["inverse_transformed_output"] = final_pred
        debug["final_predicted_3h_turbidity_FTU"] = final_pred
        log.info("[SoSe9 debug] %s", debug)
        return (final_pred, debug) if return_debug else final_pred

    df = pd.DataFrame([shifted])[feature_cols]
    final_pred = float(model.predict(df)[0])
    debug["raw_model_output"] = final_pred
    debug["final_predicted_3h_turbidity_FTU"] = final_pred
    log.info("[SoSe9 debug] %s", debug)
    return (final_pred, debug) if return_debug else final_pred
