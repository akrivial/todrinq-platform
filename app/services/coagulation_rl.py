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

from app.models.coagulation.rl.rl_models_fast import UnifiedCoagulationEnv
from model.physics_layer import PhysicsLayer, ModifiedBatchNormalization


BASE_DIR = Path(__file__).resolve().parent.parent

RL_MODEL_PATH = BASE_DIR / "models" / "coagulation" / "rl" / "dqn_best.keras"
SUPERVISED_MODEL_PATH = BASE_DIR / "models" / "coagulation" / "optimal_model_neural_network.keras"

ACTION_MAP = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]


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


def get_dosage_suggestion(online_data_dict: dict) -> dict:
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
    predicted_outlet_turbidity = _extract_model_prediction(kwr_prediction_raw)

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
    best_action_idx = int(np.argmax(q_values[0]))

    recommended_fecl3_mg_per_l = float(ACTION_MAP[best_action_idx])

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
        "validation_status": "under validation",
        "validation_message": (
            "RL #5 is advisory support only. Verify ACTION_MAP, dosing-flow unit conversion, "
            "and model-output interpretation with Greg before final release."
        ),
        "kwr_soft_sensor_used": {
            "name": "Estimation of turbidity of the coagulation-flocculation process",
            "sensor_name": "SoSe #8",
            "sensor_type": "soft sensor",
            "role": "predicts outlet turbidity used by the RL environment",
        },
        "predicted_outlet_turbidity": {
            "value": predicted_outlet_turbidity,
            "unit": "NTU / model output",
            "source": "KWR SoSe #8 coagulation soft sensor",
        },
        "recommended_fecl3_concentration": {
            "value": recommended_fecl3_mg_per_l,
            "unit": "mg/L",
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
            "predicted_effluent_turbidity": predicted_outlet_turbidity,
            "predicted_effluent_turbidity_unit": "NTU / model output",
            "confidence_status": "under validation",
            "timestamp": None,
        },
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
