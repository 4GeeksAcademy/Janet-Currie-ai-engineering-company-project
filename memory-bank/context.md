# Context — HealthCore Digital (active)

## Goal

Milestone 9 Part 1 only: turn an uploaded institutional PDF into a pollable RFP intake ticket. The existing staff UI and FastAPI app accept the file, the existing Celery worker runs a dedicated graph under `data/pipelines/rfp_intake/`, and Revenue Cycle sees department workstreams. Part 2 drafting and Part 3 arbitration are out of scope. The contract is archived at [`archive/2026-11-27-milestone-9-part-1/milestone-9-part-1-context.md`](archive/2026-11-27-milestone-9-part-1/milestone-9-part-1-context.md).

## Scope (this iteration)

- Authenticated `/backoffice/rfp` upload and ticket polling in `uis/web`.
- `POST /rfp/tickets` returns `202` after an opaque save under repo-root `data/raw/<ticket_id>.pdf`. Conversion and models run only in the worker.
- SQLModel tickets, metadata, department sections, and the Part 2 handoff on `DATABASE_URL`. `init_db()` creates the tables. No Alembic.
- Deterministic privacy gate before any RFP model call. The staff-agent graph and `app/agent/privacy.py` stay unchanged.
- Classifier, parallel `revenue` / `clinical` / `compliance` workers, and synthesizer. Status values are `analyzing`, `discarded`, and `intake_complete`.

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

Completed iterations (do not load unless asked): `archive/2026-07-29-monorepo-ai-frontend/` through `archive/2026-11-27-milestone-9-part-1/`.

## Relevant files

| Path | Role |
|------|------|
| `CONTEXT.md` | Canonical company briefing |
| `docs/architecture_proposal.md` | Backend blueprint |
| `memory-bank/implementation-memory/index.md` | Durable implementation catalog |
| `archive/2026-11-13-agent-memory/agent-memory-context.md` | Archived agent-memory handoff |
| `archive/2026-11-18-agent-gaurdrails/agent-gaurdrails-context.md` | Archived harness handoff |
| `services/api/app/agent/` | Support agent, harness, privacy gate, and memory store. Do not add RFP nodes |
| `uis/web/src/components/KnowledgeAssistant.tsx` | Staff entry for the compliance agent |
| `archive/2026-11-27-milestone-9-part-1/milestone-9-part-1-context.md` | Archived Part 1 contract |
| `data/pipelines/rfp_intake/` | Dedicated intake graph |
| `services/api/app/rfp/` | Ticket persistence and upload orchestration |
| `uis/web/src/app/(protected)/backoffice/rfp/page.tsx` | Staff intake page |
