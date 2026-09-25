# Tech updates — Serialization audit

- FastAPI 0.141.1 (`>=0.115`); Pydantic 2.13.4 (`>=2.9.0`, `ConfigDict`).
- FastAPI 0.141 stores included routers as `_IncludedRouter`; route-matrix tests walk `original_router.routes` to reach `APIRoute`.
- Public register output is `UserRegisteredResponse` (`id`, `role`, `is_active`). Authenticated user routes keep `UserPublic` including email.
- `GET /health` uses `HealthResponse`. Incident analyze uses `IncidentAnalysisResponse` in `app/incidents/schemas.py`. Export is documented `text/csv`.
- `DeliveryPublic` / `ConsumptionPublic` set `from_attributes=True` for SQLModel rows.
