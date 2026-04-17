from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/docs", include_in_schema=False)
def pretty_docs():
    with open("static/docs/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
