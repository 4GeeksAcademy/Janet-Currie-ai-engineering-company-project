# Progress — Active iteration

## Current state

Working branch is `agent-memory`. The agent-memory handoff is archived at `memory-bank/archive/2026-11-13-agent-memory/agent-memory-context.md`. User-scoped confirm-before-save memory remains in the support agent. The tool door remains in `mcps/healthcore-company-tools`. Policy search and the incident lookup stay in place.

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

## Validation results

- `uv --directory services/api run pytest tests/test_memory_privacy.py tests/test_memory_consolidation.py tests/test_agent_memory.py tests/test_agent.py`: 38 passed, 1 existing deprecation warning.
- `uv --directory services/api run pytest ../../tests/pipelines/test_agent_graph.py ../../tests/pipelines/test_agent_tools.py`: 12 passed.
- `uv --directory services/api run pytest`: 239 passed, 1 skipped, 1 existing deprecation warning.
- Live model answers, Qdrant indexing, Recall@3, and MCP Playground were not run. The local env still has no 4Geeks model ids or key.

## Blockers

No 4Geeks model ids or API key are in the local env files. Live model answers, including a live memory proposal from the model, stay unverified until those settings are filled in. The tests use a fake model.

## Next steps

1. Publishing `agent-memory` is a separate request.
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

Last updated: 2026-11-13
