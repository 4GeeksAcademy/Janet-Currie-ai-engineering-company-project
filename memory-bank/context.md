# Context — HealthCore Digital (active)

## Goal

Add a fail-closed protection harness around the Part 1 staff agent so it serves as the HealthCore compliance assistant. Check each turn before RAG, MCP, answer generation, and memory side effects. Release every answer through one output check. The handoff is [`agent-gaurdrails-context.md`](../agent-gaurdrails-context.md). Part 1 memory stays as built; its handoff is archived.

## Scope (this iteration)

- Screen `POST /agent/query` before memory confirmation, retrieval, and the incident tool. Restricted turns return a fixed template and do not call those downstream steps.
- Keep the Part 1 contract: `{ "answer", "run_id", "conversation_id", "memory_proposal" }`, user-owned confirm-before-save, and the memory privacy gate.
- Use an agent-only compliance system message. `POST /knowledge/query` keeps the coordinator prompt and its current contract. The staff page calls the agent.
- Do not add compliance policy documents. Missing evidence tells staff to contact Compliance. Tests use labeled synthetic fixtures.
- Durable checkpoints and traces still omit question and answer text, and they no longer store an incident id.
- Record sanitized block and redirect events. A local command prints session counts. No new HTTP report route.

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

Completed iterations (do not load unless asked): `archive/2026-07-29-monorepo-ai-frontend/` through `archive/2026-11-13-agent-memory/`.

## Relevant files

| Path | Role |
|------|------|
| `CONTEXT.md` | Canonical company briefing |
| `docs/architecture_proposal.md` | Backend blueprint |
| `memory-bank/implementation-memory/index.md` | Durable implementation catalog |
| `archive/2026-11-13-agent-memory/agent-memory-context.md` | Archived agent-memory handoff |
| `agent-gaurdrails-context.md` | Milestone 8 Part 2 harness handoff |
| `services/api/app/agent/` | Support agent, harness, privacy gate, and memory store |
| `uis/web/src/components/KnowledgeAssistant.tsx` | Staff entry for the compliance agent |
