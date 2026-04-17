from fastapi import APIRouter

router = APIRouter()


@router.get("/overview")
def distribution_overview():
    return {
        "module": "Distribution",
        "description": "Distribution module for downstream biological stability monitoring.",
        "work_package": "WP4",
        "water_utility": "Waternet #DC1",
        "sensors": [
            {
                "name": "SoSe #11",
                "full_name": "Aeromonas prediction model",
                "type": "soft sensor",
                "description": (
                    "Predicts the likelihood and dynamics of Aeromonas occurrence in the "
                    "distribution system, acting as an indicator of biological instability "
                    "and potential microbial regrowth in treated drinking water."
                ),
                "status_in_platform": "Under evaluation / subject to change"
            }
        ]
    }


@router.get("/sose-11/latest")
def distribution_sose_11_latest():
    return {
        "module": "Distribution",
        "sensor_name": "SoSe #11",
        "full_name": "Aeromonas prediction model",
        "sensor_type": "soft sensor",
        "location": "Distribution",
        "work_package": "WP4",
        "water_utility": "Waternet #DC1",
        "description": (
            "Predicts the likelihood and dynamics of Aeromonas occurrence in the "
            "distribution system, acting as an indicator of biological instability "
            "and potential microbial regrowth in treated drinking water."
        ),
        "status": "under evaluation / subject to change"
    }