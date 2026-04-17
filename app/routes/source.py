from fastapi import APIRouter

router = APIRouter()


@router.get("/overview")
def source_overview():
    return {
        "module": "Source / Intake",
        "description": "Source module for inlet conditions and source-related soft sensors.",
        "work_package": "WP4",
        "water_utility": "Waternet #DC1",
        "sensors": [
            {
                "name": "SoSe #9",
                "full_name": "Early prediction of turbidity in DWTP inlet",
                "type": "soft sensor",
                "description": "Predicts raw water turbidity up to 3 hours ahead",
                "status_in_platform": "Implemented",
            }
        ]
    }


@router.get("/sose-9/latest")
def source_sose_9_latest():
    return {
        "module": "Source / Intake",
        "sensor_name": "SoSe #9",
        "full_name": "Early prediction of turbidity in DWTP inlet",
        "sensor_type": "soft sensor",
        "location": "Source / Intake",
        "work_package": "WP4",
        "water_utility": "Waternet #DC1",
        "description": "Predicts raw water turbidity up to 3 hours ahead",
        "status": "connected placeholder"
    }