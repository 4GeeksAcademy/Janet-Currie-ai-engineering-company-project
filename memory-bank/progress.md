# Progress — Active iteration

## Current state

Working branch is `milestone-9`. Milestone 9 Part 1 is implemented in the existing API, Celery worker, and staff UI. Part 2 and Part 3 are not started. The Part 1 contract is archived. Live Meridian, Thames, and MedFlow uploads are unverified because `LLM_API_KEY`, `LLM_BASE_URL`, and `GENERATION_MODEL_ID` are empty. Docker is not running, so the API and worker images were not rebuilt.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory backoffice UI, Docker Compose, Web Vitals, serialization, caching, telemetry, clinic-supply pipeline, nightly telemetry export, Redis/Celery message queue, sales-forecast feasibility (unsupported vs seasonal-naive), regression-model evaluation (overfitting; do not stage).

## Completed (this iteration)

- Added opaque PDF intake at `POST /rfp/tickets`, ticket reads, and reprocess on the same ticket. Tables are created by the existing `init_db()`.
- Added `data/pipelines/rfp_intake/` and Celery task `app.tasks.rfp_intake`. The privacy gate runs before any model call. `intake_complete` is one transaction.
- Added `/backoffice/rfp` inside the existing staff shell, with the nav label `RFP intake`.
- A broker failure returns HTTP 503 with the same ticket. The page keeps that ticket visible and shows the fixed retry message.
- Pinned `markitdown==0.0.1a3` in the API requirements. Readability stays local because `textstat` shadowed the API tests.
- Archived the contract at `memory-bank/archive/2026-11-27-milestone-9-part-1/milestone-9-part-1-context.md`.

## Earlier iterations still in force

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

- From `services/api`: `uv run pytest ../../tests/pipelines/rfp_intake -q` passed (20 tests) before the full suite.
- From `services/api`: `uv run pytest tests/test_rfp_api.py tests/test_rfp_persistence.py tests/test_rfp_task.py tests/test_serialization_audit.py -q` passed (17 tests).
- From `services/api`: `uv run pytest -q --tb=line` passed: 275 passed, 1 skipped, 1 existing deprecation warning, in 135.03s. This suite does not collect `tests/pipelines/rfp_intake`.
- `npm test -w uis/web -- --watchAll=false src/lib/__tests__/rfp.test.ts src/components/__tests__/RfpIntake.test.tsx`: 8 passed. `npm run typecheck -w uis/web` completed with no errors.
- `docker compose config --quiet` completed with no errors. Images were not rebuilt.
- Host API on temporary SQLite, with Redis unset: anonymous `GET /rfp/tickets` returned 401. A signed-in synthetic PDF returned 503 `analyzing` / `failed`, detail reason `processing_failed`, fixed message, no stored path or original filename. One opaque `data/raw/<ticket_id>.pdf` was written and then removed.
- Browser: unsigned `/backoffice/rfp` redirected to `/login`. Password entry and token injection were blocked, so the signed-in page upload was not exercised in the browser. Jest covers multipart upload, no double submit, polling, three owners, and fixed messages.
- PHI marker checks are in `tests/pipelines/rfp_intake/test_privacy.py` and `test_graph.py`. Those tests passed in the pipeline run. A live PDF containing the markers was not uploaded.

## Prior validation still relevant

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

1. When `LLM_API_KEY`, `LLM_BASE_URL`, and `GENERATION_MODEL_ID` are set, upload the Meridian, Thames, and MedFlow PDFs through the signed-in page and record the three outcomes.
2. With Docker running, rebuild the API and worker images and confirm both containers see `data/raw`.
3. Knowledge-helper live scoring stays separate: set the two model ids and `RAG_MIN_SCORE`, then run `python -m process.rag` and `python data/eval/recall_at_3.py`. Do not invent those values.

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

Last updated: 2026-11-27
