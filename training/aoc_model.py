import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import joblib
import os

# Reproducibility
np.random.seed(42)

# Generate synthetic data
n_samples = 300
data = pd.DataFrame({
    "ozone_dose": np.random.uniform(0.5, 5.0, n_samples),
    "contact_time": np.random.uniform(5, 30, n_samples),
    "toc": np.random.uniform(1, 6, n_samples),
})

# Simulated AOC output: simple relationship + noise
data["aoc"] = (
    0.5 * data["ozone_dose"]
    - 0.2 * data["contact_time"]
    + 0.3 * data["toc"]
    + np.random.normal(0, 0.5, n_samples)
)

# Split data
X = data[["ozone_dose", "contact_time", "toc"]]
y = data["aoc"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Train model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Save model
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/aoc_model.pkl")

# Save plot
plt.figure(figsize=(8, 5))
plt.scatter(y_test, model.predict(X_test), alpha=0.7)
plt.xlabel("Actual AOC")
plt.ylabel("Predicted AOC")
plt.title("AOC Prediction: Actual vs Predicted")
plt.grid(True)
os.makedirs("visualizations", exist_ok=True)
plt.savefig("visualizations/aoc_prediction_plot.png")
plt.close()

print("AOC model trained and saved!")
