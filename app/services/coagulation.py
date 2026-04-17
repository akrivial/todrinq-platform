from tensorflow import keras
import os

# Get absolute path to model
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "coagulation",
    "optimal_model_neural_network.keras"
)

# Load model ONCE (important)
model = keras.models.load_model(MODEL_PATH)


def predict_coagulation(input_data):
    """
    input_data: already preprocessed data (for now)
    """
    prediction = model.predict(input_data)
    return prediction