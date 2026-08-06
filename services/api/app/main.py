"""FastAPI application for HealthCore incident analysis (Phase 2)."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Make incidents-analysis package importable as `src.*`
_REPO_ROOT = Path(__file__).resolve().parents[3]
_INCIDENTS_ANALYSIS = _REPO_ROOT / "incidents-analysis"
if str(_INCIDENTS_ANALYSIS) not in sys.path:
    sys.path.insert(0, str(_INCIDENTS_ANALYSIS))

from app.routers import incidents  # noqa: E402

app = FastAPI(
    title="HealthCore API",
    description="Phase 2 incident analysis endpoints (reuses incidents-analysis logic).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incidents.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
