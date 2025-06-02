import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
import os

np.random.seed(42)

# Step 1: Generate synthetic data for 10 years
n_semesters = 20
samples_per_semester = 6
total_samples = n_semesters * samples_per_semester

data = pd.DataFrame({
    "flowrate": np.random.normal(150, 10, total_samples),
    "influent_toc": np.random.normal(5.0, 0.5, total_samples),
    "effluent_toc": np.random.normal(1.2, 0.3, total_samples),
    "bed_age": np.tile(np.arange(100, 160), n_semesters)[:total_samples],
    "biological_activity": np.random.normal(0.4, 0.05, total_samples),
    "clogging_index": np.random.normal(70, 10, total_samples)
})

data["delta_toc"] = data["influent_toc"] - data["effluent_toc"]
data["cumulative_load"] = data["flowrate"] * data["delta_toc"]
data["semester_id"] = np.repeat(np.arange(n_semesters), samples_per_semester)

agg = data.groupby("semester_id").agg({
    "flowrate": "mean",
    "influent_toc": "mean",
    "effluent_toc": "mean",
    "bed_age": "mean",
    "biological_activity": "mean",
    "clogging_index": "mean",
    "delta_toc": "mean",
    "cumulative_load": "sum"
}).reset_index()

agg["estimated_saturation_percent"] = np.clip(
    (agg["cumulative_load"] / agg["cumulative_load"].max()) * 100 +
    np.random.normal(0, 5, len(agg)), 0, 100)

agg["needs_regeneration_this_month"] = agg["estimated_saturation_percent"] > 70

# Train models
features = agg.drop(columns=["semester_id", "estimated_saturation_percent", "needs_regeneration_this_month"])
X_train, _, y_cls_train, _ = train_test_split(features, agg["needs_regeneration_this_month"], test_size=0.2)
X_train_reg, _, y_reg_train, _ = train_test_split(features, agg["estimated_saturation_percent"], test_size=0.2)

clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_cls_train)

reg = RandomForestRegressor(n_estimators=100, random_state=42)
reg.fit(X_train_reg, y_reg_train)

# Wrapper model
class CarbonTimeSeriesModel:
    def __init__(self, classifier, regressor):
        self.classifier = classifier
        self.regressor = regressor

    def predict(self, X):
        return {
            "needs_regeneration_this_month": bool(self.classifier.predict(X)[0]),
            "estimated_saturation_percent": float(self.regressor.predict(X)[0])
        }

model = CarbonTimeSeriesModel(clf, reg)
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/train_carbon_timeseries_model_upload.pkl")

print("✅ train_carbon_timeseries_model_upload.pkl saved in models directory.")
