from pathlib import Path
from functools import lru_cache

import numpy as np
import pandas as pd
import keras

from app.models.coagulation.rl.rl_models import DQNAgent, UnifiedCoagulationEnv
from model.physics_layer import PhysicsLayer, ModifiedBatchNormalization


BASE_DIR = Path(__file__).resolve().parent.parent

RL_MODEL_PATH = BASE_DIR / "models" / "coagulation" / "rl" / "dqn_best.keras"
SUPERVISED_MODEL_PATH = BASE_DIR / "models" / "coagulation" / "optimal_model_neural_network.keras"

ACTION_MAP = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]


@lru_cache(maxsize=1)
def load_supervised_model():
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
    # state_dim = 7 input features
    # action_dim = 8 discrete dosage actions
    state_dim = 7
    action_dim = len(ACTION_MAP)

    agent = DQNAgent(state_dim=state_dim, action_dim=action_dim)
    agent.model.load_weights(RL_MODEL_PATH)
    return agent.model


def get_dosage_suggestion(online_data_dict: dict) -> dict:
    dqn_model = load_rl_agent()
    supervised_model = load_supervised_model()

    df_input = pd.DataFrame([online_data_dict])

    temp_env = UnifiedCoagulationEnv(
        df_input,
        supervised_model,
        mode="discrete",
    )

    state, _ = temp_env.reset()
    state_input = np.array(state, dtype=np.float32).reshape(1, -1)

    q_values = dqn_model.predict(state_input, verbose=0)
    best_action_idx = int(np.argmax(q_values[0]))
    recommended_dosage = ACTION_MAP[best_action_idx]

    return {
        "module": "Treatment",
        "process": "Coagulation",
        "sensor_name": "RL #1",
        "sensor_type": "soft sensor",
        "model_type": "reinforcement learning",
        "recommended_fecl3_dosage_mg_per_l": float(recommended_dosage),
        "selected_action_index": best_action_idx,
        "q_values": [float(x) for x in q_values[0]],
        "input_data": online_data_dict,
    }