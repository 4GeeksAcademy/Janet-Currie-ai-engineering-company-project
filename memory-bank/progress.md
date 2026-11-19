# Progress — Active iteration

## Current state

Working branch is `agent-gaurdrails`. The compliance harness is in the Part 1 staff agent. Each turn is screened before memory confirmation, retrieval, and MCP. Unsafe model output is replaced and a staged proposal from that turn is voided. The staff knowledge page calls `POST /agent/query` and keeps `conversation_id`. Live model answers and Qdrant search stay unverified.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory backoffice UI, Docker Compose, Web Vitals, serialization, caching, telemetry, clinic-supply pipeline, nightly telemetry export, Redis/Celery message queue, sales-forecast feasibility (unsupported vs seasonal-naive), regression-model evaluation (overfitting; do not stage).

## Completed (this iteration)

- Recorded the knowledge-helper scope and narrowed the API library ban.
- Copied the four English policy documents into `docs/company-knowledge-base/`.
- Added `setup` / `embed` in `data/process/rag.py` and `retrieve` / `generate_answer` / `query` in `data/pipelines/rag.py`.
- Added signed-in `POST /knowledge/query`, the staff page at `/knowledge`, Qdrant in Compose, and `docs/rag/rag-design.md`.
- The cutter produces 14 pieces: insurance 3, appointments 4, referrals 4, new patients 3. A live Qdrant load has not been run.
- Added the compiled support-agent map and signed-in `POST /agent/query`. `POST /knowledge/query` still calls `query()`.
- An empty agent search returns one fixed sentence and does not call the writing model. A Georgia Medicaid trace is saved at `data/eval/agent-trace-example.json`.
- The latest incident upload now keeps safe rows in the existing store. `patient_id` is dropped. The agent map chooses policy search, one incident read, or both.
- Added the read-only tool door. The staff token now carries issuer `https://healthcore-api`, audience `healthcore-company-tools`, and scopes `incidents:read inventory:read`. The agent incident step calls `get_incident_status` through that door.
- Archived the handoff at `memory-bank/archive/2026-11-12-mcp-oauth-tools/mcp-oauth-tools-context.md`.
- Added user-scoped confirm-before-save memory in `services/api/app/agent/`. Policy search and the incident lookup stay. No staff page and no Celery cleanup job.
- Archived the handoff at `memory-bank/archive/2026-11-13-agent-memory/agent-memory-context.md`.
- Added the compliance harness in `services/api/app/agent/harness.py`, with screening before the existing graph, untrusted-data filtering, and one output release check.
- Pointed the staff knowledge page at `POST /agent/query`. `POST /knowledge/query` still uses the coordinator prompt.
- Added `uv run python -m app.agent.guard_summary` for sanitized session counts.
- Archived the handoff at `memory-bank/archive/2026-11-18-agent-gaurdrails/agent-gaurdrails-context.md`.

## Validation results

- `uv --directory services/api run pytest tests/test_agent_harness.py tests/test_agent.py tests/test_agent_memory.py tests/test_memory_privacy.py tests/test_knowledge.py`: 62 passed, 1 existing deprecation warning.
- `uv --directory services/api run pytest ../../tests/pipelines/test_agent_graph.py ../../tests/pipelines/test_agent_tools.py`: 12 passed.
- `uv --directory services/api run pytest`: 263 passed, 1 skipped, 1 existing deprecation warning.
- `npm test -w uis/web -- --watchAll=false src/components/__tests__/KnowledgeAssistant.test.tsx`: 6 passed. `npm run typecheck -w uis/web` completed with no errors.
- Staff page in the browser: a signed-in "Hello" rendered the compliance redirect as the answer. The next request to `POST /agent/query` included the returned `conversation_id`. An in-domain referral question reached that route and the page showed the existing sanitized error after HTTP 503, because local search and the writing model are not configured.
- `uv --directory services/api run python -m app.agent.guard_summary` printed the local session below. It contains codes only.

```json
{
  "counts_by_category": {"content": 2, "security": 2, "structural": 0},
  "counts_by_guard": {
    "external": {"content": 0, "security": 0, "structural": 0},
    "intake": {"content": 0, "security": 2, "structural": 0},
    "output": {"content": 0, "security": 0, "structural": 0},
    "scope": {"content": 2, "security": 0, "structural": 0}
  },
  "session_boundary": "AGENT_GUARD_SESSION plus AGENT_GUARD_LOG",
  "session_id": "local",
  "total": 4
}
```

- Live model answers, Qdrant indexing, Recall@3, and MCP Playground were not run. The local env still has no 4Geeks model ids or key. The configured inventory database was unreachable, so the browser check used a temporary SQLite file.

## Blockers

No 4Geeks model ids or API key are in the local env files. Live model answers, including a live memory proposal from the model, stay unverified until those settings are filled in. The tests use a fake model.

## Next steps

1. Publishing `agent-gaurdrails` is a separate request. The syllabus branch name is `feature/agent-guardrails`.
2. When the 4Geeks settings exist, set the two model ids and `RAG_MIN_SCORE`, run `python -m process.rag`, then `python data/eval/recall_at_3.py`. Do not invent those values.

## Run commands (durable)

```bash
uv sync --directory scripts/sales_forecast --group dev
uv --directory scripts/sales_forecast run pytest
uv --directory scripts/sales_forecast run python ../train_sales_forecast.py
uv --directory scripts/sales_forecast run python ../eval_sales_forecast.py
cd services/api && uv run pytest
uv --directory mcps/healthcore-company-tools run pytest
services/api/.venv/bin/python -m pytest tests/pipelines/test_rag.py
uv --directory services/api run pytest ../../tests/pipelines/test_agent_graph.py ../../tests/pipelines/test_agent_tools.py
uv --directory services/api run python ../../data/process/rag.py
uv --directory services/api run python ../../data/eval/recall_at_3.py
python3 data/pipelines/pipeline.py
./services/api/.venv/bin/python scripts/nightly_export.py
docker compose up --build
```

Last updated: 2026-11-18
