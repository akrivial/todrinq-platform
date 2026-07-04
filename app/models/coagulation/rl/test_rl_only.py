import numpy as np
import tensorflow as tf

model = tf.keras.models.load_model("dqn_best.keras", compile=False)

print("Loaded!")

print("Input shape:", model.input_shape)
print("Output shape:", model.output_shape)

n_features = model.input_shape[-1]

state = np.array([[0.8] * n_features], dtype=np.float32)

q_values = model.predict(state)

print("Q-values:", q_values)

action = int(np.argmax(q_values[0]))

print("Selected action:", action)