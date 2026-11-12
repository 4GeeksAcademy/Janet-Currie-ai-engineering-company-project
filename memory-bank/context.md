# Context — HealthCore Digital (active)

## Goal

Add a locked HealthCore tool door under `mcps/` and send the support agent's incident step through that door. The handoff is [`mcp-oauth-tools-context.md`](../mcp-oauth-tools-context.md).

## Scope (this iteration)

- One MCP server at `mcps/healthcore-company-tools`. It reads one saved incident and reads stock. It does not create incidents or change stock.
- The door checks the existing staff login token with MCP Auth. The token gains two labels: `incidents:read` and `inventory:read`.
- The agent keeps the same policy-versus-incident choice. The incident step calls the door. The staff token stays out of the saved graph state.
- Do not add a staff page, a second incident database, or a Docker service for the door.

## Scope (standing)

- Keep shipped UIs runnable: `uis/website` (public), `uis/web` (staff JWT, including inventory).
- Phase 1 incident CLI: [`scripts/`](../scripts/).
- Phase 2 API: incidents, suppliers, staff JWT auth, inventory, telemetry, reporting, Celery queue.
- Sales forecast CLI: [`scripts/train_sales_forecast.py`](../scripts/train_sales_forecast.py) and [`scripts/eval_sales_forecast.py`](../scripts/eval_sales_forecast.py) (isolated `scripts/sales_forecast` uv env).
- Local stack: `docker compose up` starts website (3000), staff UI (3001), FastAPI (8000), Redis (6379), worker, Flower (5555).
- Treat [`docs/architecture_proposal.md`](../docs/architecture_proposal.md) as the blueprint before expanding beyond Phase 2.
- Do **not** invent production PHI flows or EHR integrations without explicit instruction.

## Constraints

- Company briefing: [`CONTEXT.md`](../CONTEXT.md) (do not edit without instruction).
- Milestone 1 static archives and Milestone 2 `src/types/**`, `src/utils/**` — import/reference only until instructed.
- APIs live only under `services/`.
- HIPAA (US) / UK GDPR apply to any patient-adjacent data handling.
- User/Profile stay in TinyDB only (`services/api/data/auth.json`).
- No commit/push/PR unless the user requests it.
- Treat implementation and validation as one task (see spec).
- Do not rewrite `memory-bank/archive/`. Leave `services/api/.coverage` untracked.
- Celery module is `app.celery_app`. Do not `load_dotenv` at Celery import time.
- Do not add sales-forecast training libraries (`scikit-learn`, `scipy`, `matplotlib`) to `services/api/pyproject.toml` or `scripts/requirements.txt`. The API project may include the Qdrant client, LangGraph, and the SQLite checkpoint package, mirrored in `services/api/requirements.txt`. Do not add those libraries to `scripts/requirements.txt`.

## Essential background

HealthCore: 12 outpatient clinics (US + UK), ~200 staff, ~$28M revenue.

Staff UI is `uis/web` (port 3001), not `uis/backoffice`. FastAPI lives at `services/api`. Browser API calls use `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

Completed iterations (do not load unless asked): `archive/2026-07-29-monorepo-ai-frontend/` through `archive/2026-11-07-regression-model-eval/`.

## Relevant files

| Path | Role |
|------|------|
| `CONTEXT.md` | Canonical company briefing |
| `docs/architecture_proposal.md` | Backend blueprint |
| `memory-bank/implementation-memory/index.md` | Durable implementation catalog |
