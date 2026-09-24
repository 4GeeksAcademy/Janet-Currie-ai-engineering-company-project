# Serialization audit

## Purpose

Make every HealthCore FastAPI success payload an explicit Pydantic projection so `uis/web` is not coupled to TinyDB/SQLModel documents and sensitive fields cannot leak.

## Final Behavior

- All 27 application JSON routes declare `response_model` on the decorator.
- `POST /users` returns `UserRegisteredResponse` (`id`, `role`, `is_active`) with no email.
- `GET /auth/me` still returns `MeResponse.email` for `fetchMe`.
- Login / forgot / reset / change-password return only `TokenResponse` or `MessageResponse`.
- `DELETE /users/{user_id}` is documented `204` with `response_model=None`.
- `GET /health` returns `HealthResponse`.
- `POST /api/incidents/analyze` returns `IncidentAnalysisResponse` (same shape as `IncidentAnalysisResult` in `uis/web`).
- Incident export is documented as `text/csv`, not JSON.
- Supplier list/detail stay on one `Supplier` model (directory table needs notes, compliance, currency, `updated_at`).
- Inventory keeps create vs public split; `GET /inventory/orders` nests `SupplySummary`, not a full catalogue row.

## Architecture and Data Flow

Schemas stay in existing modules: `app/auth/models.py`, `app/inventory/schemas.py`, `app/suppliers/models.py`. Incident output lives in `app/incidents/schemas.py`. `summary_to_json` still maps the CLI summary; the Pydantic model is the HTTP contract. Write bodies ignore extra server-managed fields (`id`, `hashed_password`, `current_stock`, `user_uuid`, `updated_at`).

## Important Files

- `docs/serialization-audit.md` — original vs final matrix
- `services/api/app/auth/models.py` — `UserRegisteredResponse`, write `extra=ignore`
- `services/api/app/routers/users.py` — register output and 204 contract
- `services/api/app/main.py` — `HealthResponse`
- `services/api/app/incidents/schemas.py` — analysis JSON
- `services/api/app/routers/incidents.py` — analyze + CSV `responses`
- `services/api/tests/test_serialization_audit.py` — matrix and payload tests

## Interfaces and Contracts

Unauthenticated success bodies must not include `email`, `password`, `hashed_password`, or reset tokens. Authenticated `GET /auth/me` includes email. Error handlers are unchanged (`422 {detail, errors}`; outbound insufficient-stock `400` `detail` string).

## Decisions and Constraints

- Do not slim `Supplier` list fields the directory renders.
- Do not use `UserPublic` as the public register schema.
- `from_attributes=True` on `DeliveryPublic` / `ConsumptionPublic` because handlers validate SQLModel rows.
- Website and `scripts/` do not call this HTTP API.

## Validation

`cd services/api && uv run pytest` — 104 passed (2026-09-23). OpenAPI `/docs` smoke without credentials: `TokenResponse`, `UserRegisteredResponse`, `OrderMovement` → `SupplySummary`.

## Maintenance Notes

When adding a route, add a `response_model` (or a documented 204/CSV `responses` map), a row in `docs/serialization-audit.md`, and an entry in `JSON_ROUTES` / `SPECIAL_ROUTES` in `test_serialization_audit.py`. FastAPI 0.141 stores included routers as `_IncludedRouter`; walk `original_router.routes` to enumerate `APIRoute`s.
