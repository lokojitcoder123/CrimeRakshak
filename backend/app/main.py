"""FastAPI application entrypoint for the Auth & RBAC module.

Run locally with::

    cd backend
    uvicorn app.main:app --reload

Only Authentication & RBAC are wired here. Graph Intelligence and Financial
Crime routers are intentionally out of scope for this step; their protected
placeholders live in ``app/routers/protected.py``.
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppHTTPException
from app.core.logging import get_logger
from app.routers import admin, auth, protected

logger = get_logger("api")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Authentication & Role-Based Access Control module.",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers → consistent error envelope ────────────────────────
@app.exception_handler(AppHTTPException)
async def app_http_exception_handler(request: Request, exc: AppHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.detail}},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "request validation failed",
                "details": exc.errors(),
            }
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(protected.router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["system"], summary="Liveness probe")
def health():
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.get("/", tags=["system"], include_in_schema=False)
def root():
    return {"service": settings.PROJECT_NAME, "docs": "/docs"}
