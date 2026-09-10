"""
RL #5 – Optimal FeCl3 dosage for coagulation.

This service connects:
Mock/PIMS input
→ KWR coagulation soft sensor (SoSe #8) for predicted outlet turbidity
→ TUD RL #5 DQN model for optimal FeCl3 dosage recommendation
→ structured platform/UI output.
"""

from pathlib import Path
from functools import lru_cache

import numpy as np
import pandas as pd
from tensorflow import keras

from app.coagulation_domain import (
    FECL3_ACTIONS_MG_L,
    FECL3_MAX_MG_L,
    FECL3_MIN_MG_L,
)
from app.models.coagulation.rl.rl_models_fast import UnifiedCoagulationEnv
from model.physics_layer import PhysicsLayer, ModifiedBatchNormalization
from app.services.data_quality import assess_operational_inputs
from app.services.model_lifecycle import model_lifecycle


BASE_DIR = Path(__file__).resolve().parent.parent

RL_MODEL_PATH = (
    BASE_DIR
    / "models"
    / "coagulation"
    / "rl"
    / "dqn_best_single_online.keras"
)
SUPERVISED_MODEL_PATH = BASE_DIR / "models" / "coagulation" / "optimal_model_neural_network.keras"

ACTION_MAP = list(FECL3_ACTIONS_MG_L)
DOSE_UNIT = "mg/L"
REQUIRED_INPUTS = (
    "ftu_raw_water",
    "fecl3_concentration",
    "temperature_raw_water",
    "ph_raw_water",
    "after_dredging",
    "lane",
    "year",
)


@lru_cache(maxsize=1)
def load_supervised_model():
    """
    Loads the KWR coagulation soft sensor.
    This model predicts outlet turbidity after coagulation-flocculation.
    """
    return keras.models.load_model(
        SUPERVISED_MODEL_PATH,
        compile=False,
        custom_objects={
            "PhysicsLayer": PhysicsLayer,
            "ModifiedBatchNormalization": ModifiedBatchNormalization,
        },
    )


@lru_cache(maxsize=1)
def load_rl_agent():
    """
    Loads the TUD RL #5 DQN model.
    """
    return keras.models.load_model(
        RL_MODEL_PATH,
        safe_mode=False,
        compile=False,
    )


def _extract_model_prediction(prediction):
    """
    Safely extracts a scalar value from different Keras prediction shapes.
    """
    arr = np.asarray(prediction)

    if arr.size == 0:
        return None

    return float(arr.reshape(-1)[0])


def _select_rl_action(*, model_input: dict, q_values, supervised_model):
    """Evaluate the DQN-selected dose with all other process conditions unchanged."""
    values = np.asarray(q_values).reshape(-1)
    if len(values) != len(ACTION_MAP) or not np.isfinite(values).all():
        raise ValueError("RL model returned invalid action values.")
    action_idx = int(np.argmax(values))
    candidate_dose = float(ACTION_MAP[action_idx])
    candidate_input = dict(model_input)
    candidate_input["fecl3_concentration"] = candidate_dose
    prediction = _extract_model_prediction(
        supervised_model.predict(pd.DataFrame([candidate_input]), verbose=0)
    )
    if prediction is None or not np.isfinite(prediction):
        raise ValueError("Soft sensor returned an invalid recommended-dose prediction.")
    return action_idx, candidate_dose, prediction, [{
        "action_index": action_idx, "dose": candidate_dose,
        "predicted_turbidity": prediction,
    }]


def get_dosage_suggestion(
    online_data_dict: dict,
    *,
    input_timestamp: str | None = None,
    data_status: str | None = None,
    maintenance_active: bool = False,
) -> dict:
    """
    Runs the RL #5 recommendation workflow.

    Workflow:
    1. Receive mock/PIMS-style coagulation input.
    2. Run the KWR coagulation soft sensor to estimate outlet turbidity.
    3. Pass the same input and KWR model into the RL environment.
    4. Let the DQN select the optimal FeCl3 action.
    5. Return recommended FeCl3 dose, KWR predicted turbidity, action index,
       Q-values, and dosing-flow conversion.
    """

    quality = assess_operational_inputs(
        online_data_dict,
        REQUIRED_INPUTS,
        observed_at=input_timestamp,
        declared_status=data_status,
        maintenance_active=maintenance_active,
    )
    lifecycle = model_lifecycle(
        family="rl_coagulation",
        name="RL #5 coagulation optimisation",
        version=RL_MODEL_PATH.name,
    )
    performance_lifecycle = model_lifecycle(
        family="coagulation_performance",
        name="KWR coagulation-performance model (SoSe #8)",
        version=SUPERVISED_MODEL_PATH.name,
    )
    current_dose = online_data_dict.get("fecl3_concentration")
    if current_dose is not None and not (
        FECL3_MIN_MG_L <= float(current_dose) <= FECL3_MAX_MG_L
    ):
        quality = {
            **quality,
            "status": "out_of_domain",
            "valid": False,
            "message": (
                f"FeCl3 concentration must be between {FECL3_MIN_MG_L:.1f} "
                f"and {FECL3_MAX_MG_L:.1f} {DOSE_UNIT} for RL #5."
            ),
            "out_of_domain_fields": ["fecl3_concentration"],
        }
    if not quality["valid"]:
        return {
            "module": "Treatment",
            "process": "Coagulation",
            "name": "Optimal FeCl3 dosage for coagulation",
            "sensor_name": "RL #5",
            "sensor_type": "reinforcement-learning advisory",
            "advisory_only": True,
            "recommendation_available": False,
            "message": quality.get(
                "message",
                "Recommendation unavailable because one or more required input "
                "values are stale or unavailable.",
            ),
            "data_quality": quality,
            "current_fecl3_dose": {
                "value": online_data_dict.get("fecl3_concentration"),
                "unit": DOSE_UNIT,
            },
            "recommended_fecl3_concentration": {"value": None, "unit": DOSE_UNIT},
            "predicted_turbidity_current_dose": {
                "value": None,
                "unit": "FTU / model output",
            },
            "predicted_turbidity_recommended_dose": {
                "value": None,
                "unit": "FTU / model output",
            },
            "model_lifecycle": lifecycle,
            "coagulation_model_lifecycle": performance_lifecycle,
            "operator_decision": "pending",
            "input_data": online_data_dict,
        }

    dqn_model = load_rl_agent()
    supervised_model = load_supervised_model()

    lane = int(online_data_dict["lane"])
    flow_key = f"flow_coagulation_{lane}"
    flow_coagulation = online_data_dict.get(flow_key)

    model_input = {
        "ftu_raw_water": online_data_dict["ftu_raw_water"],
        "fecl3_concentration": online_data_dict["fecl3_concentration"],
        "temperature_raw_water": online_data_dict["temperature_raw_water"],
        "ph_raw_water": online_data_dict["ph_raw_water"],
        "after_dredging": online_data_dict["after_dredging"],
        "lane": online_data_dict["lane"],
        "year": online_data_dict["year"],
    }

    df_input = pd.DataFrame([model_input])

    # ------------------------------------------------------------
    # KWR SoSe #8 prediction
    # ------------------------------------------------------------
    # This is the explicit KWR coagulation soft-sensor prediction.
    # It estimates the outlet turbidity after coagulation-flocculation
    # based on the same mock/PIMS input used by RL #5.
    kwr_prediction_raw = supervised_model.predict(df_input, verbose=0)
    predicted_current_turbidity = _extract_model_prediction(kwr_prediction_raw)

    # ------------------------------------------------------------
    # TUD RL #5 recommendation
    # ------------------------------------------------------------
    # The RL environment also receives the KWR supervised model.
    # Internally, UnifiedCoagulationEnv uses the KWR model as its
    # simulation/evaluation environment for the FeCl3 dosing actions.
    temp_env = UnifiedCoagulationEnv(
        df_input,
        supervised_model,
        mode="discrete",
    )

    state, _ = temp_env.reset()
    state_input = np.array(state, dtype=np.float32).reshape(1, -1)

    q_values = dqn_model.predict(state_input, verbose=0)
    raw_best_action_idx = int(np.argmax(q_values[0]))
    (
        best_action_idx,
        recommended_fecl3_mg_per_l,
        predicted_recommended_turbidity,
        evaluated_actions,
    ) = _select_rl_action(
        model_input=model_input,
        q_values=q_values[0],
        supervised_model=supervised_model,
    )

    recommended_dosing_flow = None
    if flow_coagulation is not None:
        recommended_dosing_flow = (
            recommended_fecl3_mg_per_l * float(flow_coagulation) / 192
        )

    return {
        "module": "Treatment",
        "process": "Coagulation",
        "name": "Optimal FeCl3 dosage for coagulation",
        "sensor_name": "RL #5",
        "sensor_type": "reinforcement-learning advisory",
        "model_type": "DQN reinforcement learning with supervised KWR coagulation model environment",
        "included_in_risk_aggregation": False,
        "advisory_only": True,
        "recommendation_available": True,
        "data_quality": quality,
        "validation_status": "under validation",
        "validation_message": (
            "RL #5 is advisory support only. The DQN-selected dose is evaluated with "
            "the same process conditions as the current-dose soft-sensor prediction. Verify "
            "ACTION_MAP units and dosing-flow conversion with the model owner."
        ),
        "recommendation_safety_check": {
            "rule": "DQN-selected dose evaluated with unchanged non-dose process inputs",
            "passed": True,
            "raw_dqn_action_index": raw_best_action_idx,
            "selected_action_index": best_action_idx,
            "evaluated_actions": evaluated_actions,
        },
        "kwr_soft_sensor_used": {
            "name": "Estimation of turbidity of the coagulation-flocculation process",
            "sensor_name": "SoSe #8",
            "sensor_type": "soft sensor",
            "role": "predicts outlet turbidity used by the RL environment",
        },
        "predicted_outlet_turbidity": {
            "value": predicted_current_turbidity,
            "unit": "NTU / model output",
            "source": "KWR SoSe #8 coagulation soft sensor",
        },
        "current_fecl3_dose": {
            "value": float(model_input["fecl3_concentration"]),
            "unit": DOSE_UNIT,
            "source": "operational input; never overwritten by recommendation",
        },
        "predicted_turbidity_current_dose": {
            "value": predicted_current_turbidity,
            "unit": "FTU / model output",
            "source": "KWR SoSe #8 using current dose",
        },
        "predicted_turbidity_recommended_dose": {
            "value": predicted_recommended_turbidity,
            "unit": "FTU / model output",
            "source": "KWR SoSe #8 using recommended dose",
        },
        "recommended_fecl3_concentration": {
            "value": recommended_fecl3_mg_per_l,
            "unit": DOSE_UNIT,
            "source": "TUD RL #5 selected action",
        },
        "recommended_fecl3_dosing_flow": {
            "value": recommended_dosing_flow,
            "unit": "plant/PIMS dosing-flow unit",
            "calculation": "recommended_fecl3_mg_per_l * flow_coagulation_lane / 192",
            "validation_warning": "TODO(Greg): confirm plant/PIMS dosing-flow unit and conversion factor 192.",
        },
        "operator_advisory": {
            "recommended_fecl3_dose": recommended_fecl3_mg_per_l,
            "unit": "mg/L",
            "predicted_effluent_turbidity": predicted_recommended_turbidity,
            "predicted_effluent_turbidity_unit": "NTU / model output",
            "confidence_status": "under validation",
            "timestamp": None,
            "statement": (
                "Advisory recommendation — the operator remains responsible "
                "for the final dosing decision."
            ),
        },
        "coagulation_targets": {
            "operational_optimisation_target": {
                "value": 4.0,
                "unit": "FTU",
                "qualifier": "approximately",
            },
            "acceptable_operational_threshold": {
                "value": 6.0,
                "unit": "FTU",
                "comparison": "below",
            },
        },
        "operator_decision": "pending",
        "operator_decision_timestamp": None,
        "model_lifecycle": lifecycle,
        "coagulation_model_lifecycle": performance_lifecycle,
        "debug": {
            "selected_action_index": best_action_idx,
            "q_values": [float(x) for x in q_values[0]],
            "note": "Developer/debug fields; do not display action index in operator UI.",
        },
        "selected_action_index": best_action_idx,
        "q_values": [float(x) for x in q_values[0]],
        "input_data": online_data_dict,
    }

# """
# RL #5 – Optimal FeCl3 dosage for coagulation.
# """

# from pathlib import Path
# from functools import lru_cache

# import numpy as np
# import pandas as pd
# from tensorflow import keras

# from app.models.coagulation.rl.rl_models_fast import UnifiedCoagulationEnv
# from model.physics_layer import PhysicsLayer, ModifiedBatchNormalization


# BASE_DIR = Path(__file__).resolve().parent.parent

# RL_MODEL_PATH = BASE_DIR / "models" / "coagulation" / "rl" / "dqn_best.keras"
# SUPERVISED_MODEL_PATH = BASE_DIR / "models" / "coagulation" / "optimal_model_neural_network.keras"

# ACTION_MAP = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]


# @lru_cache(maxsize=1)
# def load_supervised_model():
#     return keras.models.load_model(
#         SUPERVISED_MODEL_PATH,
#         compile=False,
#         custom_objects={
#             "PhysicsLayer": PhysicsLayer,
#             "ModifiedBatchNormalization": ModifiedBatchNormalization,
#         },
#     )


# @lru_cache(maxsize=1)
# def load_rl_agent():
#     return keras.models.load_model(
#         RL_MODEL_PATH,
#         safe_mode=False,
#         compile=False,
#     )


# def get_dosage_suggestion(online_data_dict: dict) -> dict:
#     dqn_model = load_rl_agent()
#     supervised_model = load_supervised_model()

#     lane = int(online_data_dict["lane"])
#     flow_key = f"flow_coagulation_{lane}"
#     flow_coagulation = online_data_dict.get(flow_key)

#     model_input = {
#         "ftu_raw_water": online_data_dict["ftu_raw_water"],
#         "fecl3_concentration": online_data_dict["fecl3_concentration"],
#         "temperature_raw_water": online_data_dict["temperature_raw_water"],
#         "ph_raw_water": online_data_dict["ph_raw_water"],
#         "after_dredging": online_data_dict["after_dredging"],
#         "lane": online_data_dict["lane"],
#         "year": online_data_dict["year"],
#     }

#     df_input = pd.DataFrame([model_input])

#     temp_env = UnifiedCoagulationEnv(
#         df_input,
#         supervised_model,
#         mode="discrete",
#     )

#     state, _ = temp_env.reset()
#     state_input = np.array(state, dtype=np.float32).reshape(1, -1)

#     q_values = dqn_model.predict(state_input, verbose=0)
#     best_action_idx = int(np.argmax(q_values[0]))

#     recommended_fecl3_mmol_per_l = float(ACTION_MAP[best_action_idx])

#     recommended_dosing_flow = None
#     if flow_coagulation is not None:
#         recommended_dosing_flow = (
#             recommended_fecl3_mmol_per_l * float(flow_coagulation) / 192
#         )

#         #ask greg are the units are fine?

#     return {
#         "module": "Treatment",
#         "process": "Coagulation",
#         "name": "Optimal FeCl3 dosage for coagulation",
#         "sensor_name": "RL #5",
#         "sensor_type": "reinforcement-learning soft sensor",
#         "model_type": "DQN reinforcement learning with supervised KWR coagulation model environment",
#         "recommended_fecl3_concentration": {
#             "value": recommended_fecl3_mmol_per_l,
#             "unit": "mg/L",
#         },
#         "recommended_fecl3_dosing_flow": {
#             "value": recommended_dosing_flow,
#             "unit": "plant/PIMS dosing-flow unit",
#             "calculation": "recommended_fecl3_mmol_per_l * flow_coagulation_lane / 192",
#         },
#         "selected_action_index": best_action_idx,
#         "q_values": [float(x) for x in q_values[0]],
#         "input_data": online_data_dict,
#     }
