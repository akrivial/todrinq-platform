"""Smoke test for the active Greg RL model artifact."""

from pathlib import Path

import numpy as np
import tensorflow as tf


MODEL_PATH = Path(__file__).with_name("dqn_best_single_online.keras")


def test_active_rl_model_contract():
    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    assert model.input_shape == (None, 7)
    assert model.output_shape == (None, 8)

    state = np.array([[0.8] * model.input_shape[-1]], dtype=np.float32)
    q_values = np.asarray(model.predict(state, verbose=0))
    assert q_values.shape == (1, 8)
    assert np.isfinite(q_values).all()
    assert 0 <= int(np.argmax(q_values[0])) < 8
