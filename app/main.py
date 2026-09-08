# soft_sensors_api/app/main.py

from pathlib import Path
import sys
import logging
import base64
import hashlib
import hmac
import os
import secrets
import time

from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse, HTMLResponse, RedirectResponse
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
from app.routes.observations import router as observations_router



# --- Rijkswaterstaat / RIWA route ---
from app.routes.rws_test import router as rws_test_router

from app.model_registry import status, ready
from app.services.observation_store import database_status, initialize_database
from app.services.prediction_scheduler import start_prediction_scheduler, stop_prediction_scheduler

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

# --- Platform protection ---
APP_TOKEN = os.getenv("TODRINQ_API_TOKEN")
LOGIN_PASSWORD = os.getenv("TODRINQ_APP_PASSWORD")
SESSION_SECRET = os.getenv("TODRINQ_SESSION_SECRET") or LOGIN_PASSWORD or secrets.token_urlsafe(32)
SESSION_COOKIE = "todrinq_session"
SESSION_TTL_SECONDS = int(os.getenv("TODRINQ_SESSION_TTL_SECONDS", "43200"))
ALLOW_QUERY_TOKEN = os.getenv("TODRINQ_ALLOW_QUERY_TOKEN", "false").lower() in {"1", "true", "yes"}
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("TODRINQ_CORS_ORIGINS", "").split(",")
    if origin.strip()
]


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _sign(value: str) -> str:
    return hmac.new(SESSION_SECRET.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def _make_session() -> str:
    expires = int(time.time()) + SESSION_TTL_SECONDS
    nonce = secrets.token_urlsafe(16)
    payload = _b64(f"operator:{expires}:{nonce}".encode("utf-8"))
    return f"{payload}.{_sign(payload)}"


def _has_valid_session(request: Request) -> bool:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie or "." not in cookie:
        return False

    payload, signature = cookie.rsplit(".", 1)
    if not hmac.compare_digest(signature, _sign(payload)):
        return False

    padded = payload + "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        _, expires, _ = decoded.split(":", 2)
        return int(expires) >= int(time.time())
    except (ValueError, UnicodeDecodeError):
        return False


def _cookie_secure(request: Request) -> bool:
    forced = os.getenv("TODRINQ_COOKIE_SECURE")
    if forced is not None:
        return forced.lower() in {"1", "true", "yes"}
    return request.headers.get("x-forwarded-proto", request.url.scheme) == "https"


def verify_platform_token(request: Request):
    if _has_valid_session(request):
        return True

    api_key = request.headers.get("x-api-key")
    if api_key and APP_TOKEN and hmac.compare_digest(api_key, APP_TOKEN):
        return True

    query_token = request.query_params.get("token")
    if ALLOW_QUERY_TOKEN and query_token and APP_TOKEN and hmac.compare_digest(query_token, APP_TOKEN):
        return True

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


@app.on_event("startup")
async def startup_services():
    initialize_database()
    start_prediction_scheduler()


@app.on_event("shutdown")
async def shutdown_services():
    await stop_prediction_scheduler()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- No-cache for UI/static assets ---
@app.middleware("http")
async def no_cache_mw(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

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

    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - Swagger UI",
    )


# --- Mount /static ---
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    logger.error("STATIC_DIR does not exist: %s", STATIC_DIR)


def _login_page(error: str = "") -> HTMLResponse:
    error_html = f'<p class="error">{error}</p>' if error else ""
    return HTMLResponse(f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ToDrinQ Login</title>
  <style>
    :root {{ color-scheme: light; --teal:#38c8dc; --navy:#0d1f3c; --line:#d8e8ef; }}
    * {{ box-sizing:border-box; }}
    body {{
      min-height:100vh; margin:0; display:grid; place-items:center;
      font-family:Inter, Arial, sans-serif; background:#f5f9fb; color:var(--navy);
    }}
    main {{
      width:min(420px, calc(100vw - 32px)); padding:32px; background:white;
      border:1px solid var(--line); border-radius:14px; box-shadow:0 18px 50px rgba(13,31,60,.10);
    }}
    h1 {{ margin:0 0 8px; font-size:1.65rem; }}
    p {{ margin:0 0 22px; color:#517083; line-height:1.45; }}
    label {{ display:block; font-weight:700; font-size:.86rem; margin-bottom:8px; }}
    input {{
      width:100%; height:46px; border:1px solid #b8d3de; border-radius:8px;
      padding:0 48px 0 12px; font:inherit; color:var(--navy);
    }}
    .password-field {{ position:relative; }}
    .password-toggle {{
      position:absolute; top:50%; right:6px; transform:translateY(-50%);
      width:38px; height:38px; margin:0; padding:0; display:grid; place-items:center;
      border:0; border-radius:6px; background:transparent; color:#517083;
      font-size:1.2rem; cursor:pointer;
    }}
    .password-toggle:hover {{ background:#edf7fa; color:var(--navy); }}
    button {{
      width:100%; height:46px; margin-top:18px; border:0; border-radius:8px;
      background:linear-gradient(135deg,var(--navy),var(--teal)); color:white;
      font-weight:800; cursor:pointer;
    }}
    .error {{ color:#b42318; font-weight:700; margin-bottom:14px; }}
  </style>
</head>
<body>
  <main>
    <h1>ToDrinQ Platform</h1>
    <p>Sign in to access the protected decision-support dashboard.</p>
    {error_html}
    <form method="post" action="/login">
      <label for="password">Platform password</label>
      <div class="password-field">
        <input id="password" name="password" type="password" autocomplete="current-password" required autofocus />
        <button class="password-toggle" id="password-toggle" type="button" aria-label="Show password" aria-pressed="false" title="Show password">&#128065;</button>
      </div>
      <button type="submit">Sign in</button>
    </form>
  </main>
  <script>
    const passwordInput = document.getElementById("password");
    const passwordToggle = document.getElementById("password-toggle");
    passwordToggle.addEventListener("click", () => {{
      const show = passwordInput.type === "password";
      passwordInput.type = show ? "text" : "password";
      passwordToggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
      passwordToggle.setAttribute("aria-pressed", String(show));
      passwordToggle.title = show ? "Hide password" : "Show password";
    }});
  </script>
</body>
</html>""")


@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    if _has_valid_session(request):
        return RedirectResponse(url="/app", status_code=303)
    return _login_page()


@app.post("/login", include_in_schema=False)
def login_submit(request: Request, password: str = Form(...)):
    if not LOGIN_PASSWORD:
        return _login_page("Platform login is not configured. Set TODRINQ_APP_PASSWORD.")

    if not LOGIN_PASSWORD or not hmac.compare_digest(password, LOGIN_PASSWORD):
        return _login_page("Invalid password.")

    response = RedirectResponse(url="/app", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        _make_session(),
        httponly=True,
        secure=_cookie_secure(request),
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )
    return response


@app.post("/logout", include_in_schema=False)
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


# --- Serve protected UI ---
def _serve_ui_html(request: Request):
    try:
        verify_platform_token(request)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)

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

app.include_router(
    observations_router,
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
        "ok": True,
        "database": database_status(),
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
