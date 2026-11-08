# Context — HealthCore Digital (active)

## Goal

Teach the support-agent map to look up one incident from the latest uploaded CSV. Policy questions still use the knowledge search. The handoff is [`langgraph-agent-base-context2.md`](../langgraph-agent-base-context2.md). Part 1 stays archived at [`archive/2026-11-07-langgraph-agent-base/langgraph-agent-base-context.md`](archive/2026-11-07-langgraph-agent-base/langgraph-agent-base-context.md).

## Scope (this iteration)

- Keep the safe fields from each uploaded incident row in the existing in-memory store. Drop `patient_id`.
- The agent reads that store directly. The wait limit is 3 seconds. Routing is a fixed id-and-word check.
- A policy question still calls `retrieve()` and `generate_answer()` in [`data/pipelines/rag.py`](../data/pipelines/rag.py). An incident status is written from the saved fields.
- Leave `POST /knowledge/query` and `POST /agent/query` in place. The agent door still returns `{ "answer", "run_id" }`.
- Do not add a stock lookup, a staff page, or a second incident database.

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
