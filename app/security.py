import os
import hmac
from fastapi import Header, HTTPException, Request

API_TOKEN = os.getenv("TODRINQ_API_TOKEN")
ALLOW_QUERY_TOKEN = os.getenv("TODRINQ_ALLOW_QUERY_TOKEN", "false").lower() in {"1", "true", "yes"}


def verify_api_token(
    request: Request,
    x_api_key: str = Header(None)
):
    query_token = request.query_params.get("token")

    if x_api_key and API_TOKEN and hmac.compare_digest(x_api_key, API_TOKEN):
        return True

    if ALLOW_QUERY_TOKEN and query_token and API_TOKEN and hmac.compare_digest(query_token, API_TOKEN):
        return True

    raise HTTPException(
        status_code=401,
        detail="Unauthorized: missing or invalid API token"
    )
