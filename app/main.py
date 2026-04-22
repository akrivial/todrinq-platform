# soft_sensors_api/app/main.py

from pathlib import Path
import sys
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles

# --- Diagnostics: confirm which Python/module/file is running ---
print(">>> PYTHON:", sys.executable)
print(">>> MAIN __file__:", __file__)

# --- Clean public routers only ---
from app.routes.predict import router as predict_router
from app.routes.risk import router as risk_router
from app.routes.ngsi_notify import router as ngsi_router
from app.routes.mock_pims import router as mock_pims_router
from app.routes.source import router as source_router
from app.routes.treatment import router as treatment_router
from app.routes.distribution import router as distribution_router

from app.model_registry import status, ready

# --- Paths (relative to THIS file) ---
APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
UI_INDEX = STATIC_DIR / "ui" / "index.html"

print(">>> APP_DIR    =", APP_DIR.resolve())
print(">>> STATIC_DIR =", STATIC_DIR.resolve())
print(">>> UI_INDEX   =", UI_INDEX.resolve())

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("soft_sensors_api")

# --- FastAPI app ---
app = FastAPI(
    title="ToDrinQ Platform Backend",
    description="Modular FIWARE-aligned backend for source, treatment, distribution, and risk evaluation.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- No-cache for UI/static assets ---
@app.middleware("http")
async def no_cache_mw(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/", "/app", "/app2", "/static/")):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# --- Mount /static ---
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    logger.error("STATIC_DIR does not exist: %s", STATIC_DIR)

# --- Serve UI ---
def _serve_ui_html():
    if UI_INDEX.exists():
        html = UI_INDEX.read_bytes()
        return Response(
            content=html,
            media_type="text/html",
            headers={
                "Cache-Control": "no-store, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-UI-From": str(UI_INDEX.resolve()),
            },
        )
    return JSONResponse(
        {"error": f"UI not found at {UI_INDEX}"},
        status_code=404,
    )

# --- UI routes ---
@app.get("/", include_in_schema=False)
def serve_ui_root():
    return _serve_ui_html()

@app.get("/app", include_in_schema=False)
def serve_ui():
    return _serve_ui_html()

@app.get("/app2", include_in_schema=False)
def serve_ui2():
    return _serve_ui_html()

# --- Public routers shown in Swagger ---
app.include_router(predict_router)
app.include_router(source_router, prefix="/source", tags=["Source Module"])
app.include_router(treatment_router, prefix="/treatment", tags=["Treatment Module"])
app.include_router(distribution_router, prefix="/distribution", tags=["Distribution Module"])
app.include_router(risk_router, prefix="/risk", tags=["Risk Module"])

# Optional demo / integration helpers
app.include_router(mock_pims_router, prefix="/pims", tags=["Mock PIMS"])
app.include_router(ngsi_router, tags=["FIWARE / NGSI-LD"])

# --- API / Health endpoints ---
@app.get("/api", tags=["System"])
def api_root():
    return {
        "message": "ToDrinQ Platform Backend is running",
        "modules": ["Source", "Treatment", "Distribution", "Risk"],
    }

@app.get("/healthz", tags=["System"])
def healthz():
    return {"ok": True}

@app.get("/readyz", tags=["System"])
def readyz():
    return {
        "ready": ready(),
        "models": status(),
    }