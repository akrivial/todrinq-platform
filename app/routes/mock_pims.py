from fastapi import APIRouter
from datetime import datetime
import random

router = APIRouter()


def generate_coagulation_data():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "ftu_raw_water": round(random.uniform(3.0, 12.0), 2),
        "fecl3_concentration": round(random.uniform(1.0, 8.0), 2),
        "temperature_raw_water": round(random.uniform(5.0, 22.0), 2),
        "ph_raw_water": round(random.uniform(6.5, 8.5), 2),
        "after_dredging": random.randint(0, 1),
        "lane": random.choice([1, 2, 3]),
        "year": datetime.utcnow().year,
    }


def generate_ct_data():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "Chamber": round(random.uniform(1, 4), 2),
        "WaterTemperature": round(random.uniform(5.0, 22.0), 2),
        "RFTurbidity": round(random.uniform(0.1, 5.0), 2),
        "FlowRate": round(random.uniform(100.0, 500.0), 2),
        "Ozonedosage": round(random.uniform(0.5, 5.0), 2),
    }


def generate_bromate_data():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "month": datetime.utcnow().month,
        "Chamber": round(random.uniform(1, 4), 2),
        "WaterTemperature": round(random.uniform(5.0, 22.0), 2),
        "RFTurbidity": round(random.uniform(0.1, 5.0), 2),
        "FlowRate": round(random.uniform(100.0, 500.0), 2),
        "Ozonedosage": round(random.uniform(0.5, 5.0), 2),
        "Residencetime": round(random.uniform(1.0, 30.0), 2),
        "WaterTemperature_1": round(random.uniform(5.0, 22.0), 2),
        "RFturbidity_1": round(random.uniform(0.1, 5.0), 2),
        "FlowRate_1": round(random.uniform(100.0, 500.0), 2),
        "Ozonedosage_1": round(random.uniform(0.5, 5.0), 2),
        "CT_All": round(random.uniform(5.0, 40.0), 2),
    }


def generate_coliform_data():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "Chamber": round(random.uniform(1, 4), 2),
        "WaterTemperature": round(random.uniform(5.0, 22.0), 2),
        "RFTurbidity": round(random.uniform(0.1, 5.0), 2),
        "FlowRate": round(random.uniform(100.0, 500.0), 2),
        "Ozonedosage": round(random.uniform(0.5, 5.0), 2),
        "RFturbidity_1": round(random.uniform(0.1, 5.0), 2),
        "CT_All": round(random.uniform(5.0, 40.0), 2),
    }


@router.get("/coagulation/latest", summary="Get latest mock coagulation input")
def get_latest_coagulation():
    return generate_coagulation_data()


@router.get("/ct/latest", summary="Get latest mock CT input")
def get_latest_ct():
    return generate_ct_data()


@router.get("/bromate/latest", summary="Get latest mock bromate input")
def get_latest_bromate():
    return generate_bromate_data()


@router.get("/coliform/latest", summary="Get latest mock coliform input")
def get_latest_coliform():
    return generate_coliform_data()


@router.get("/overview", summary="Get all latest mock PIMS streams")
def get_mock_pims_overview():
    return {
        "coagulation": generate_coagulation_data(),
        "ct": generate_ct_data(),
        "bromate": generate_bromate_data(),
        "coliform": generate_coliform_data(),
    }