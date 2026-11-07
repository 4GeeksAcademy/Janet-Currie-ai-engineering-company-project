# Context — HealthCore Digital (active)

## Goal

Implement Ticket **#DEV-55**: Redis + Celery + Flower so JWT `POST /reporting/pipeline-runs` is queued, processed by an independent worker, pollable at `GET /tasks/{task_id}`, retried with exponential backoff, and recorded in a durable dead-letter table after exhaustion. Contract: [`message-queue-context.md`](../message-queue-context.md). Plan: [`docs/queues/message-queue-implementation-plan.md`](../docs/queues/message-queue-implementation-plan.md).

## Scope (this iteration)

- Add Redis (broker/result only), a Celery worker, and Flower to the existing Compose stack.
- Convert one existing slow API (`POST /reporting/pipeline-runs`) to `202` + `task_id`.
- JWT `GET /tasks/{task_id}` with public states `pending | started | success | failure`.
- SQLModel `dead_letter_tasks` on existing `DATABASE_URL`.
- Focused tests, operator docs, local live validation.

Out of scope: Celery Beat, replacing nightly/`job_runs`/`pipeline_runs`, moving inventory cache to Redis, dashboard rewrite, Alembic, unauthorized git publish.

## Scope (standing)

- Keep shipped UIs runnable: `uis/website` (public), `uis/web` (staff JWT, including inventory).
- Phase 1 incident CLI: [`scripts/`](../scripts/).
- Phase 2 API: incidents, suppliers, staff JWT auth, inventory, telemetry, reporting.
- Local stack: `docker compose up` starts website (3000), staff UI (3001), and FastAPI (8000); this ticket also adds Redis (6379), worker, and Flower (5555).
- Treat [`docs/architecture_proposal.md`](../docs/architecture_proposal.md) as the blueprint before expanding beyond Phase 2.
- Do **not** invent production PHI flows or EHR integrations without explicit instruction.

## Constraints

- Company briefing: [`CONTEXT.md`](../CONTEXT.md) (do not edit without instruction).
- Milestone 1 static archives and Milestone 2 `src/types/**`, `src/utils/**` — import/reference only until instructed.
- APIs live only under `services/`.
- HIPAA (US) / UK GDPR apply to any patient-adjacent data handling.
- User/Profile stay in TinyDB only (`services/api/data/auth.json`). Do not add User/Profile tables in Postgres/Supabase.
- No commit/push/PR unless the user requests it.
- Treat implementation and validation as one task (see spec).
- Do not rewrite error handlers, replace FastAPI/Pydantic/SQLModel/TinyDB, or create a new backend.
- Do not rewrite `memory-bank/archive/`. Leave `services/api/.coverage` untracked.
- Celery module is `app.celery_app` (image WORKDIR `/app/services/api`), not `services.celery_app`.
- Do not `load_dotenv` at Celery import time (pytest isolation).

## Essential background

HealthCore: 12 outpatient clinics (US + UK), ~200 staff, ~$28M revenue.

Staff UI is `uis/web` (port 3001), not `uis/backoffice`. FastAPI lives at `services/api`. Browser API calls use `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`. The public website and `scripts/` do not call this HTTP API.

Completed iterations (do not load unless asked): `archive/2026-07-29-monorepo-ai-frontend/`, `archive/2026-08-28-supplier-directory/`, `archive/2026-08-28-staff-auth/`, `archive/2026-08-31-error-handling/`, `archive/2026-09-04-bullet-proof/`, `archive/2026-09-18-inventory-api/`, `archive/2026-09-18-inventory-backoffice-ui/`, `archive/2026-09-23-docker-compose/`, `archive/2026-09-23-web-vitals/`, `archive/2026-09-24-serialization/`, `archive/2026-09-30-caching-optimisation/`, `archive/2026-10-14-telemetry/`, `archive/2026-10-21-data-pipeline/`, `archive/2026-11-04-background-processes/`.

## Relevant files

| Path | Role |
|------|------|
| `message-queue-context.md` | DEV-55 phase guide |
| `docs/queues/message-queue-implementation-plan.md` | Execution plan |
| `docker-compose.yml` | `ui` + `backend` plus redis/worker/flower |
| `services/api/app/celery_app.py` | Celery application (`-A app.celery_app`) |
| `services/api/app/tasks/` | Pipeline task + DLQ |
| `services/api/app/routers/reporting.py` | 202 producer |
| `services/api/app/routers/tasks.py` | `GET /tasks/{task_id}` |
| `data/pipelines/pipeline.py` | Existing ETL (`execute_monthly_clinic_supply_performance`) |
| `CACHING_REPORT.md` | Caching investigation trail (keep at repo root; still in-process TTL) |
| `services/api/app/main.py` | FastAPI entry |
| `uis/web/` | Staff JWT app |
| `uis/website/` | Public site |
