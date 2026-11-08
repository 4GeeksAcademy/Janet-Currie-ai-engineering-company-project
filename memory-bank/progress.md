# Progress — Active iteration

## Current state

Active work is the support-agent map on branch `langgraph-agent-base`. The handoff is root `langgraph-agent-base-context.md`. The knowledge helper handoff stays at [`archive/2026-11-07-rag-knowledge-base/rag-knowledge-base-context.md`](archive/2026-11-07-rag-knowledge-base/rag-knowledge-base-context.md). `retrieve()` and `generate_answer()` stay in `data/pipelines/rag.py`.

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

## Validation results

- `uv --directory services/api run pytest ../../tests/pipelines/test_agent_graph.py`: 6 passed.
- `services/api/.venv/bin/python -m pytest tests/pipelines/test_rag.py`: 15 passed.
- `uv --directory services/api run pytest`: 206 passed, 1 skipped.
- `npm run typecheck`: passed for the website and the staff app.
- `docker compose config`: passed.
- Live model answers, the real match score, and Recall@3 were not run. The local env still has no 4Geeks model ids or key. `recall_at_3.py` was not run again; the earlier run exited 2 because `LLM_API_KEY`, `LLM_BASE_URL`, `EMBEDDING_MODEL_ID`, and `GENERATION_MODEL_ID` are empty.
- No new staff page was added, so the agent door was not opened in a browser.

## Blockers

No 4Geeks model ids or API key are in the local env files. Live model answers, vector size, the real match score, live indexing, and Recall@3 stay unverified until those settings are filled in.

## Next steps

1. Publishing `langgraph-agent-base` is a separate request.
2. When the 4Geeks settings exist, set the two model ids and `RAG_MIN_SCORE`, run `python -m process.rag`, then `python data/eval/recall_at_3.py`. Do not invent those values.

## Run commands (durable)

```bash
uv sync --directory scripts/sales_forecast --group dev
uv --directory scripts/sales_forecast run pytest
uv --directory scripts/sales_forecast run python ../train_sales_forecast.py
uv --directory scripts/sales_forecast run python ../eval_sales_forecast.py
cd services/api && uv run pytest
services/api/.venv/bin/python -m pytest tests/pipelines/test_rag.py
uv --directory services/api run pytest ../../tests/pipelines/test_agent_graph.py
uv --directory services/api run python ../../data/process/rag.py
uv --directory services/api run python ../../data/eval/recall_at_3.py
python3 data/pipelines/pipeline.py
./services/api/.venv/bin/python scripts/nightly_export.py
docker compose up --build
```

Last updated: 2026-11-07
