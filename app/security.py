import os
from fastapi import Header, HTTPException, Request

API_TOKEN = os.getenv("TODRINQ_API_TOKEN", "todrinq-demo-2026")


def verify_api_token(
    request: Request,
    x_api_key: str = Header(None)
):
    query_token = request.query_params.get("token")

    if x_api_key == API_TOKEN or query_token == API_TOKEN:
        return True

    raise HTTPException(
        status_code=401,
        detail="Unauthorized: missing or invalid API token"
    )