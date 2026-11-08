# Progress — Active iteration

## Current state

Active work is the coordinator knowledge helper on branch `rag-knowledge-base`. The handoff is root `rag-knowledge-base-context.md`. Regression-model evaluation stays archived at [`archive/2026-11-07-regression-model-eval/`](archive/2026-11-07-regression-model-eval/). The fit report remains `data/eval/evaluation_report.md`.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory backoffice UI, Docker Compose, Web Vitals, serialization, caching, telemetry, clinic-supply pipeline, nightly telemetry export, Redis/Celery message queue, sales-forecast feasibility (unsupported vs seasonal-naive), regression-model evaluation (overfitting; do not stage).

## Completed (this iteration)

- Recorded the knowledge-helper scope and narrowed the API library ban.
- Copied the four English policy documents into `docs/company-knowledge-base/`.
- Added `setup` / `embed` in `data/process/rag.py` and `retrieve` / `generate_answer` / `query` in `data/pipelines/rag.py`.
- Added signed-in `POST /knowledge/query`, the staff page at `/knowledge`, Qdrant in Compose, and `docs/rag/rag-design.md`.
- The cutter produces 14 pieces: insurance 3, appointments 4, referrals 4, new patients 3. A live Qdrant load has not been run.

## Validation results

- `services/api/.venv/bin/python -m pytest tests/pipelines/test_rag.py`: 15 passed.
- `uv --directory services/api run pytest`: 201 passed, 1 skipped.
- `npm test -w uis/web -- src/components/__tests__/KnowledgeAssistant.test.tsx`: 5 passed.
- `npm run typecheck -w uis/web`: passed.
- `docker compose config`: passed.
- `uv --directory services/api run python ../../data/eval/recall_at_3.py`: not scored. Exit 2 because `LLM_API_KEY`, `LLM_BASE_URL`, `EMBEDDING_MODEL_ID`, and `GENERATION_MODEL_ID` are empty.
- Live `POST /knowledge/query` with a local user: empty question returns 422; a real question returns 503 "The knowledge assistant is not configured. Please try again later."
- Browser: signed-out `/knowledge` shows "Redirecting to sign in…". The signed-in form was not clicked in the browser because typing a password into the browser was blocked. Jest covers the form.

## Blockers

No 4Geeks model ids or API key are in the local env files. Vector size, minimum score, live indexing, and Recall@3 are unverified until those settings are filled in.

## Next steps

1. Put the real embedding model id, a different writing model id, the base URL, and the key into the local env. Do not commit them.
2. Start Qdrant, run `uv --directory services/api run python ../../data/process/rag.py`, then tune `RAG_MIN_SCORE` until Recall@3 is at least 80% and the off-topic question still matches nothing.
3. Write those measured values into `docs/rag/rag-design.md`.

## Run commands (durable)

```bash
uv sync --directory scripts/sales_forecast --group dev
uv --directory scripts/sales_forecast run pytest
uv --directory scripts/sales_forecast run python ../train_sales_forecast.py
uv --directory scripts/sales_forecast run python ../eval_sales_forecast.py
cd services/api && uv run pytest
services/api/.venv/bin/python -m pytest tests/pipelines/test_rag.py
uv --directory services/api run python ../../data/process/rag.py
uv --directory services/api run python ../../data/eval/recall_at_3.py
python3 data/pipelines/pipeline.py
./services/api/.venv/bin/python scripts/nightly_export.py
docker compose up --build
```

Last updated: 2026-11-07
