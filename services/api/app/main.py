"""FastAPI application for HealthCore Digital."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# Make scripts/ package importable as `src.*` (Phase 1 shared library)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from app.database import init_db
from app.cache import response_cache
from app.middleware import RequestTimingMiddleware
from app.routers import auth, incidents, inventory, profiles, suppliers, users  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield
    response_cache.clear()


app = FastAPI(
    title="HealthCore API",
    description="Incident analysis, supplier directory, staff authentication, and inventory.",
    version="0.4.0",
    lifespan=lifespan,
)

DEFAULT_CORS_ORIGINS = (
    "http://localhost:3001",
    "http://127.0.0.1:3001",
)


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return list(DEFAULT_CORS_ORIGINS)
    return [part.strip() for part in raw.split(",") if part.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestTimingMiddleware)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(profiles.router)
app.include_router(incidents.router)
app.include_router(suppliers.router)
app.include_router(inventory.router)


@app.exception_handler(RequestValidationError)
async def pydantic_validation_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Surface Pydantic validation errors clearly for the backoffice form."""
    errors = []
    for err in exc.errors():
        loc_parts = [str(p) for p in err.get("loc", ()) if p != "body"]
        errors.append(
            {
                "field": ".".join(loc_parts) or "body",
                "message": err.get("msg", "Invalid value"),
            }
        )
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "errors": errors},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, StarletteHTTPException):
        return await http_exception_handler(request, exc)
    if isinstance(exc, RequestValidationError):
        return await pydantic_validation_handler(request, exc)
    logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong. Please try again."},
    )


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
