# soft_sensors_api/app/main.py

from pathlib import Path
import sys
import logging

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

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
from app.routes.synthetic import router as synthetic_router
from app.routes.coagulation_rl import router as coagulation_rl_router



# --- Rijkswaterstaat / RIWA route ---
from app.routes.rws_test import router as rws_test_router

from app.model_registry import status, ready

# --- Paths ---
APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
UI_INDEX = STATIC_DIR / "ui" / "index.html"

print(">>> APP_DIR    =", APP_DIR.resolve())
print(">>> STATIC_DIR =", STATIC_DIR.resolve())
print(">>> UI_INDEX   =", UI_INDEX.resolve())

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("soft_sensors_api")

# --- Platform token ---
APP_TOKEN = "todrinq-demo-2026"


def verify_platform_token(request: Request):
    token = request.query_params.get("token")

    if token != APP_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    return True


# --- FastAPI app ---
# Disable default public docs/openapi. We create protected ones below.
app = FastAPI(
    title="ToDrinQ Platform Backend",
    description="Modular FIWARE-aligned backend for source, treatment, distribution, and risk evaluation.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
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


# --- Protected OpenAPI schema ---
@app.get("/openapi.json", include_in_schema=False)
def protected_openapi(request: Request):
    verify_platform_token(request)

    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


# --- Protected Swagger UI ---
@app.get("/docs", include_in_schema=False)
def protected_docs(request: Request):
    verify_platform_token(request)

    token = request.query_params.get("token")

    return get_swagger_ui_html(
        openapi_url=f"/openapi.json?token={token}",
        title=f"{app.title} - Swagger UI",
    )


# --- Mount /static ---
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    logger.error("STATIC_DIR does not exist: %s", STATIC_DIR)


# --- Serve protected UI ---
def _serve_ui_html(request: Request):
    verify_platform_token(request)

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
def serve_ui_root(request: Request):
    return _serve_ui_html(request)


@app.get("/app", include_in_schema=False)
def serve_ui(request: Request):
    return _serve_ui_html(request)


@app.get("/app2", include_in_schema=False)
def serve_ui2(request: Request):
    return _serve_ui_html(request)


# --- Protected routers ---
app.include_router(
    predict_router,
    dependencies=[Depends(verify_platform_token)]
)

app.include_router(
    source_router,
    prefix="/source",
    tags=["Source Module"],
    dependencies=[Depends(verify_platform_token)]
)

app.include_router(
    treatment_router,
    prefix="/treatment",
    tags=["Treatment Module"],
    dependencies=[Depends(verify_platform_token)]
)

app.include_router(
    coagulation_rl_router,
    prefix="/treatment",
    tags=["Treatment Module"],
    dependencies=[Depends(verify_platform_token)]
)

app.include_router(
    distribution_router,
    prefix="/distribution",
    tags=["Distribution Module"],
    dependencies=[Depends(verify_platform_token)]
)

app.include_router(
    risk_router,
    prefix="/risk",
    tags=["Risk Module"],
    dependencies=[Depends(verify_platform_token)]
)

app.include_router(
    synthetic_router,
    dependencies=[Depends(verify_platform_token)]
)

app.include_router(
    rws_test_router,
    tags=["Source Hard Sensors - Rijkswaterstaat"],
    dependencies=[Depends(verify_platform_token)]
)

app.include_router(
    mock_pims_router,
    prefix="/pims",
    tags=["Mock PIMS"],
    dependencies=[Depends(verify_platform_token)]
)

app.include_router(
    ngsi_router,
    tags=["FIWARE / NGSI-LD"],
    dependencies=[Depends(verify_platform_token)]
)


# --- API / Health endpoints ---
@app.get("/api", tags=["System"], dependencies=[Depends(verify_platform_token)])
def api_root():
    return {
        "message": "ToDrinQ Platform Backend is running",
        "modules": [
            "Source",
            "Treatment",
            "Distribution",
            "Risk"
        ],
    }


# Keep public for Docker/App Runner health checks
@app.get("/healthz", tags=["System"])
def healthz():
    return {
        "ok": True
    }


@app.get("/version", tags=["System"])
def version():
    return {
        "version": "synthetic-token-fix-2026-06-04",
        "synthetic_auth": "query_token_only"
    }


@app.get("/readyz", tags=["System"], dependencies=[Depends(verify_platform_token)])
def readyz():
    return {
        "ready": ready(),
        "models": status(),
    }
# @app.get("/healthz", tags=["System"])
# def healthz():
#     return {
#         "ok": True
#     }


# @app.get("/readyz", tags=["System"], dependencies=[Depends(verify_platform_token)])
# def readyz():
#     return {
#         "ready": ready(),
#         "models": status(),
#     }

# # soft_sensors_api/app/main.py

# from pathlib import Path
# import sys
# import logging

# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import Response, JSONResponse
# from fastapi.staticfiles import StaticFiles

# # --- Diagnostics: confirm which Python/module/file is running ---
# print(">>> PYTHON:", sys.executable)
# print(">>> MAIN __file__:", __file__)

# # --- Clean public routers only ---
# from app.routes.predict import router as predict_router
# from app.routes.risk import router as risk_router
# from app.routes.ngsi_notify import router as ngsi_router
# from app.routes.mock_pims import router as mock_pims_router
# from app.routes.source import router as source_router
# from app.routes.treatment import router as treatment_router
# from app.routes.distribution import router as distribution_router
# from app.routes.synthetic import router as synthetic_router

# # NEW: Rijkswaterstaat / RIWA test route
# from app.routes.rws_test import router as rws_test_router

# from app.model_registry import status, ready

# # --- Paths (relative to THIS file) ---
# APP_DIR = Path(__file__).resolve().parent
# STATIC_DIR = APP_DIR / "static"
# UI_INDEX = STATIC_DIR / "ui" / "index.html"

# print(">>> APP_DIR    =", APP_DIR.resolve())
# print(">>> STATIC_DIR =", STATIC_DIR.resolve())
# print(">>> UI_INDEX   =", UI_INDEX.resolve())

# # --- Logging ---
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("soft_sensors_api")

# # --- FastAPI app ---
# app = FastAPI(
#     title="ToDrinQ Platform Backend",
#     description="Modular FIWARE-aligned backend for source, treatment, distribution, and risk evaluation.",
#     version="1.0.0",
#     docs_url="/docs",
#     redoc_url=None,
# )

# # --- CORS ---
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # --- No-cache for UI/static assets ---
# @app.middleware("http")
# async def no_cache_mw(request: Request, call_next):
#     response = await call_next(request)
#     if request.url.path.startswith(("/", "/app", "/app2", "/static/")):
#         response.headers["Cache-Control"] = "no-store, max-age=0"
#         response.headers["Pragma"] = "no-cache"
#         response.headers["Expires"] = "0"
#     return response

# # --- Mount /static ---
# if STATIC_DIR.exists():
#     app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# else:
#     logger.error("STATIC_DIR does not exist: %s", STATIC_DIR)

# # --- Serve UI ---
# def _serve_ui_html():
#     if UI_INDEX.exists():
#         html = UI_INDEX.read_bytes()
#         return Response(
#             content=html,
#             media_type="text/html",
#             headers={
#                 "Cache-Control": "no-store, max-age=0",
#                 "Pragma": "no-cache",
#                 "Expires": "0",
#                 "X-UI-From": str(UI_INDEX.resolve()),
#             },
#         )
#     return JSONResponse(
#         {"error": f"UI not found at {UI_INDEX}"},
#         status_code=404,
#     )

# # --- UI routes ---
# @app.get("/", include_in_schema=False)
# def serve_ui_root():
#     return _serve_ui_html()

# @app.get("/app", include_in_schema=False)
# def serve_ui():
#     return _serve_ui_html()

# @app.get("/app2", include_in_schema=False)
# def serve_ui2():
#     return _serve_ui_html()

# # --- Public routers shown in Swagger ---
# app.include_router(predict_router)
# app.include_router(source_router, prefix="/source", tags=["Source Module"])
# app.include_router(treatment_router, prefix="/treatment", tags=["Treatment Module"])
# app.include_router(distribution_router, prefix="/distribution", tags=["Distribution Module"])
# app.include_router(risk_router, prefix="/risk", tags=["Risk Module"])

# # --- Synthetic data for NTUA ---
# app.include_router(synthetic_router)

# # NEW: Rijkswaterstaat / RIWA hard-sensor test route
# app.include_router(rws_test_router, tags=["Source Hard Sensors - Rijkswaterstaat"])

# # Optional demo / integration helpers
# app.include_router(mock_pims_router, prefix="/pims", tags=["Mock PIMS"])
# app.include_router(ngsi_router, tags=["FIWARE / NGSI-LD"])

# # --- API / Health endpoints ---
# @app.get("/api", tags=["System"])
# def api_root():
#     return {
#         "message": "ToDrinQ Platform Backend is running",
#         "modules": ["Source", "Treatment", "Distribution", "Risk"],
#     }

# @app.get("/healthz", tags=["System"])
# def healthz():
#     return {"ok": True}

# @app.get("/readyz", tags=["System"])
# def readyz():
#     return {
#         "ready": ready(),
#         "models": status(),
#     }


# # # soft_sensors_api/app/main.py

# # from pathlib import Path
# # import sys
# # import logging

# # from fastapi import FastAPI, Request
# # from fastapi.middleware.cors import CORSMiddleware
# # from fastapi.responses import Response, JSONResponse
# # from fastapi.staticfiles import StaticFiles

# # from app.routes.synthetic import router as synthetic_router

# # # --- Diagnostics: confirm which Python/module/file is running ---
# # print(">>> PYTHON:", sys.executable)
# # print(">>> MAIN __file__:", __file__)

# # # --- Clean public routers only ---
# # from app.routes.predict import router as predict_router
# # from app.routes.risk import router as risk_router
# # from app.routes.ngsi_notify import router as ngsi_router
# # from app.routes.mock_pims import router as mock_pims_router
# # from app.routes.source import router as source_router
# # from app.routes.treatment import router as treatment_router
# # from app.routes.distribution import router as distribution_router

# # from app.model_registry import status, ready

# # # --- Paths (relative to THIS file) ---
# # APP_DIR = Path(__file__).resolve().parent
# # STATIC_DIR = APP_DIR / "static"
# # UI_INDEX = STATIC_DIR / "ui" / "index.html"

# # print(">>> APP_DIR    =", APP_DIR.resolve())
# # print(">>> STATIC_DIR =", STATIC_DIR.resolve())
# # print(">>> UI_INDEX   =", UI_INDEX.resolve())

# # # --- Logging ---
# # logging.basicConfig(level=logging.INFO)
# # logger = logging.getLogger("soft_sensors_api")



# # # --- FastAPI app ---
# # app = FastAPI(
# #     title="ToDrinQ Platform Backend",
# #     description="Modular FIWARE-aligned backend for source, treatment, distribution, and risk evaluation.",
# #     version="1.0.0",
# #     docs_url="/docs",
# #     redoc_url=None,
# # )

# # #---synthetic data for NTUA:
# # app.include_router(synthetic_router)

# # # --- CORS ---
# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=["*"],
# #     allow_credentials=True,
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )

# # # --- No-cache for UI/static assets ---
# # @app.middleware("http")
# # async def no_cache_mw(request: Request, call_next):
# #     response = await call_next(request)
# #     if request.url.path.startswith(("/", "/app", "/app2", "/static/")):
# #         response.headers["Cache-Control"] = "no-store, max-age=0"
# #         response.headers["Pragma"] = "no-cache"
# #         response.headers["Expires"] = "0"
# #     return response

# # # --- Mount /static ---
# # if STATIC_DIR.exists():
# #     app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# # else:
# #     logger.error("STATIC_DIR does not exist: %s", STATIC_DIR)

# # # --- Serve UI ---
# # def _serve_ui_html():
# #     if UI_INDEX.exists():
# #         html = UI_INDEX.read_bytes()
# #         return Response(
# #             content=html,
# #             media_type="text/html",
# #             headers={
# #                 "Cache-Control": "no-store, max-age=0",
# #                 "Pragma": "no-cache",
# #                 "Expires": "0",
# #                 "X-UI-From": str(UI_INDEX.resolve()),
# #             },
# #         )
# #     return JSONResponse(
# #         {"error": f"UI not found at {UI_INDEX}"},
# #         status_code=404,
# #     )

# # # --- UI routes ---
# # @app.get("/", include_in_schema=False)
# # def serve_ui_root():
# #     return _serve_ui_html()

# # @app.get("/app", include_in_schema=False)
# # def serve_ui():
# #     return _serve_ui_html()

# # @app.get("/app2", include_in_schema=False)
# # def serve_ui2():
# #     return _serve_ui_html()

# # # --- Public routers shown in Swagger ---
# # app.include_router(predict_router)
# # app.include_router(source_router, prefix="/source", tags=["Source Module"])
# # app.include_router(treatment_router, prefix="/treatment", tags=["Treatment Module"])
# # app.include_router(distribution_router, prefix="/distribution", tags=["Distribution Module"])
# # app.include_router(risk_router, prefix="/risk", tags=["Risk Module"])

# # # Optional demo / integration helpers
# # app.include_router(mock_pims_router, prefix="/pims", tags=["Mock PIMS"])
# # app.include_router(ngsi_router, tags=["FIWARE / NGSI-LD"])

# # # --- API / Health endpoints ---
# # @app.get("/api", tags=["System"])
# # def api_root():
# #     return {
# #         "message": "ToDrinQ Platform Backend is running",
# #         "modules": ["Source", "Treatment", "Distribution", "Risk"],
# #     }

# # @app.get("/healthz", tags=["System"])
# # def healthz():
# #     return {"ok": True}

# # @app.get("/readyz", tags=["System"])
# # def readyz():
# #     return {
# #         "ready": ready(),
# #         "models": status(),
# #     }
