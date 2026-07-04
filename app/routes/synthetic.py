from fastapi import APIRouter
import json
from pathlib import Path

router = APIRouter(
    prefix="/synthetic",
    tags=["Synthetic Data"]
)

# Path to your JSON files
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data_models" / "synthetic_examples"


def load_json(filename):
    file_path = DATA_DIR / filename

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/sose8/kwr-coagulation")
def get_sose8():
    return load_json(
        "kwr_coagulation_synthetic_generated.json"
    )


@router.get("/sose9/turbidity-inlet")
def get_sose9():
    return load_json(
        "sose9_synthetic_generated.json"
    )


@router.get("/sose10/ozonation")
def get_sose10():
    return load_json(
        "sose10_ozonation_synthetic_generated.json"
    )


@router.get("/rl5/coagulation-dose")
def get_rl5():
    return load_json(
        "rl5_synthetic_generated.json"
    )
# from fastapi import APIRouter, Depends
# from app.security import verify_api_token

# import json
# from pathlib import Path

# router = APIRouter(
#     prefix="/synthetic",
#     tags=["Synthetic Data"]
# )

# # Path to your JSON files
# BASE_DIR = Path(__file__).resolve().parents[2]
# DATA_DIR = BASE_DIR / "data_models" / "synthetic_examples"


# def load_json(filename):
#     file_path = DATA_DIR / filename

#     with open(file_path, "r", encoding="utf-8") as f:
#         return json.load(f)


# @router.get(
#     "/sose8/kwr-coagulation",
#     dependencies=[Depends(verify_api_token)]
# )
# def get_sose8():

#     return load_json(
#         "kwr_coagulation_synthetic_generated.json"
#     )


# @router.get(
#     "/sose9/turbidity-inlet",
#     dependencies=[Depends(verify_api_token)]
# )
# def get_sose9():

#     return load_json(
#         "sose9_synthetic_generated.json"
#     )


# @router.get(
#     "/sose10/ozonation",
#     dependencies=[Depends(verify_api_token)]
# )
# def get_sose10():

#     return load_json(
#         "sose10_ozonation_synthetic_generated.json"
#     )


# @router.get(
#     "/rl5/coagulation-dose",
#     dependencies=[Depends(verify_api_token)]
# )
# def get_rl5():

#     return load_json(
#         "rl5_synthetic_generated.json"
#     )