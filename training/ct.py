# training/ct.py

import numpy as np
import pandas as pd
import joblib
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

# Fix seed
np.random.seed(42)

# Generate synthetic data
n = 300
df = pd.DataFrame({
    "disinfectant_dose": np.random.normal(2, 0.5, n),
    "tank_volume": np.random.normal(1000, 200, n),
    "flow_rate": np.random.normal(120, 20, n),
})

# Simulate CT value
df["ct_value"] = (
    df["disinfectant_dose"] * df["tank_volume"] / df["flow_rate"]
    + np.random.normal(0, 5, n)
)

# Train/test split
X = df.drop("ct_value", axis=1)
y = df["ct_value"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Train model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Save model
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/ct_model.pkl")

print("CT model trained and saved.")
