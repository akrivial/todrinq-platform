from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import joblib
import numpy as np
import os
import logging
import pandas as pd
from io import StringIO

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Waternet Soft Sensors API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Graceful model loading
def load_model(path, model_name):
    if os.path.exists(path):
        logger.info(f"Model {model_name} loaded successfully.")
        return joblib.load(path)
    else:
        logger.warning(f"Model for {model_name} not available.")
        return None

# Load models
carbon_model = load_model("models/carbon_model.pkl", "carbon")
carbon_timeseries_model = load_model("models/carbon_timeseries_model.pkl", "carbon_timeseries")
aoc_model = load_model("models/aoc_model.pkl", "aoc")
turbidity_model = load_model("models/turbidity.pkl", "turbidity")
ct_model = load_model("models/ct_model.pkl", "ct")

# Health Check
@app.get("/")
def root():
    return {"message": "✅ Waternet Soft Sensors API is running"}

# 1. Single-point carbon model
class CarbonInput(BaseModel):
    flowrate: float
    influent_toc: float
    effluent_toc: float
    bed_age: int
    biological_activity: float
    clogging_index: float

    class Config:
        json_schema_extra = {
            "example": {
                "flowrate": 150.0,
                "influent_toc": 5.0,
                "effluent_toc": 1.2,
                "bed_age": 130,
                "biological_activity": 0.4,
                "clogging_index": 80.0
            }
        }

@app.post("/predict/carbon_activation")
def predict_carbon(data: CarbonInput):
    if not carbon_model:
        return {"error": "Carbon model not available"}
    delta_toc = data.influent_toc - data.effluent_toc
    features = np.array([[data.flowrate, data.influent_toc, data.effluent_toc,
                          data.bed_age, data.biological_activity,
                          data.clogging_index, delta_toc]])
    prediction = carbon_model.predict(features)[0]
    return {"needs_regeneration": bool(prediction)}

# 2. Time-series carbon model
class CarbonTimeSeriesInput(BaseModel):
    flowrate: list[float]
    influent_toc: list[float]
    effluent_toc: list[float]
    bed_age: list[int]
    biological_activity: list[float]
    clogging_index: list[float]

    class Config:
        json_schema_extra = {
            "example": {
                "flowrate": [150.0, 148.0, 152.0],
                "influent_toc": [5.0, 5.1, 4.9],
                "effluent_toc": [1.2, 1.3, 1.1],
                "bed_age": [120, 125, 130],
                "biological_activity": [0.42, 0.4, 0.38],
                "clogging_index": [70.0, 72.5, 74.0]
            }
        }

@app.post("/predict/carbon_activation/timeseries")
def predict_carbon_timeseries(data: CarbonTimeSeriesInput):
    if not carbon_timeseries_model:
        return {"error": "Carbon time-series model not available"}

    delta_toc = np.array(data.influent_toc) - np.array(data.effluent_toc)

    features = np.array([[
        np.mean(data.flowrate),
        np.mean(data.influent_toc),
        np.mean(data.effluent_toc),
        np.mean(data.bed_age),
        np.mean(data.biological_activity),
        np.mean(data.clogging_index),
        np.mean(delta_toc),
        np.sum(np.array(data.flowrate) * delta_toc)
    ]])

    prediction = carbon_timeseries_model.predict(features)
    return {
        "needs_regeneration_this_month": bool(prediction["needs_regeneration_this_month"]),
        "estimated_saturation_percent": float(prediction["estimated_saturation_percent"])
    }

# 3. AOC Model
class AOCInput(BaseModel):
    ozone_dose: float
    contact_time: float
    toc: float

    class Config:
        json_schema_extra = {
            "example": {
                "ozone_dose": 5.0,
                "contact_time": 20.0,
                "toc": 3.5
            }
        }

@app.post("/predict/aoc")
def predict_aoc(data: AOCInput):
    if not aoc_model:
        return {"error": "AOC model not available"}
    features = np.array([[data.ozone_dose, data.contact_time, data.toc]])
    prediction = aoc_model.predict(features)[0]
    return {"aoc_prediction": float(prediction)}

# 4. Turbidity Model
class TurbidityInput(BaseModel):
    flow: float
    coagulant_dose: float
    pH: float
    temperature: float

    class Config:
        json_schema_extra = {
            "example": {
                "flow": 100.0,
                "coagulant_dose": 5.0,
                "pH": 7.0,
                "temperature": 15.0
            }
        }

@app.post("/predict/turbidity")
def predict_turbidity(data: TurbidityInput):
    if not turbidity_model:
        return {"error": "Turbidity model not available"}
    features = np.array([[data.flow, data.coagulant_dose, data.pH, data.temperature]])
    prediction = turbidity_model.predict(features)[0]
    return {"turbidity_prediction": float(prediction)}

# 5. CT Model
class CTInput(BaseModel):
    disinfectant_dose: float
    tank_volume: float
    flow_rate: float

    class Config:
        json_schema_extra = {
            "example": {
                "disinfectant_dose": 2.0,
                "tank_volume": 1000.0,
                "flow_rate": 120.0
            }
        }

@app.post("/predict/ct")
def predict_ct(data: CTInput):
    if not ct_model:
        return {"error": "CT model not available"}
    features = np.array([[data.disinfectant_dose, data.tank_volume, data.flow_rate]])
    prediction = ct_model.predict(features)[0]
    return {"ct_prediction": float(prediction)}

# 6. Upload CSV for Carbon Timeseries Prediction
@app.post("/predict/carbon_activation/upload")
def predict_carbon_from_csv(file: UploadFile = File(...)):
    if not carbon_timeseries_model:
        return {"error": "Carbon time-series model not available"}

    contents = file.file.read()
    try:
        df = pd.read_csv(StringIO(contents.decode("utf-8")))
    except Exception as e:
        return {"error": f"Failed to read CSV: {e}"}

    required = ["flowrate", "influent_toc", "effluent_toc", "bed_age", "biological_activity", "clogging_index"]
    if not all(col in df.columns for col in required):
        return {"error": f"CSV must contain columns: {required}"}

    delta_toc = df["influent_toc"] - df["effluent_toc"]
    features = np.array([[
        df["flowrate"].mean(),
        df["influent_toc"].mean(),
        df["effluent_toc"].mean(),
        df["bed_age"].mean(),
        df["biological_activity"].mean(),
        df["clogging_index"].mean(),
        delta_toc.mean(),
        (df["flowrate"] * delta_toc).sum()
    ]])

    result = carbon_timeseries_model.predict(features)
    return {
        "needs_regeneration_this_month": bool(result["needs_regeneration_this_month"]),
        "estimated_saturation_percent": float(result["estimated_saturation_percent"])
    }
