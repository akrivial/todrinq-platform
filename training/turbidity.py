# training/turbidity.py

import numpy as np
import pandas as pd
import joblib
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

# Set seed
np.random.seed(42)

# Create synthetic data
n = 300
df = pd.DataFrame({
    "flow": np.random.normal(100, 20, n),
    "coagulant_dose": np.random.normal(5, 1, n),
    "pH": np.random.normal(7, 0.5, n),
    "temperature": np.random.normal(15, 5, n),
})

# Simulate turbidity outcome
df["turbidity"] = (
    50
    - 0.4 * df["coagulant_dose"]
    - 2 * np.abs(df["pH"] - 7)
    - 0.3 * df["temperature"]
    + np.random.normal(0, 1.5, n)
)

# Train/test split
X = df.drop("turbidity", axis=1)
y = df["turbidity"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Train model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Save model
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/turbidity.pkl")

print("Turbidity model trained and saved.")
