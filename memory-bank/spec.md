# Spec — Active iteration

## Requirements

1. Memory bank follows global layout: `context.md`, `spec.md`, `progress.md`, `decisions.md`, and `archive/YYYY-MM-DD-name/` (with `implementation-plan.md` and `tech-updates.md` when archiving).
2. Root memory files stay limited to the **active** iteration plus standing facts. Completed work lives under `archive/`. Do not read `archive/` unless the user asks.
3. Agents update `progress.md` (and `decisions.md` when material) after milestones, scope changes, validation, blockers, or handoffs.
4. Delivery gates: scoped `.agents/rules/`, `skills/pre-delivery-verification` before UI/agent-doc commits, protected paths untouched without instruction.
5. Backend expansion follows [`docs/architecture_proposal.md`](../docs/architecture_proposal.md) (modular monolith under `services/healthcore-api`, region-split residency, API owns analytics).
6. **Testing and edge cases:** implementation and validation are one task. Add or update focused tests for new/changed behavior and bug fixes; prefer public interfaces; cover realistic edge cases; run the narrowest relevant checks first. Do not weaken tests to make the implementation pass. If a check cannot be run, state the limitation and what remains unverified. Docs-only changes need no runtime tests.
7. Shipped auth stays as documented in standing behavior below (TinyDB User/Profile, JWT bearer, `uis/web` localStorage, Resend reset). `uis/website` stays fully public. The AUTH course contract is archived — do not load it unless asked.
8. Error-handling is archived — do not load it unless asked. User-facing errors remain sanitized (no raw `detail`, stacks, or status codes in the UI), **except** outbound HTTP `400` insufficient-stock `detail`, which is shown inline as designed staff copy.
9. Bullet-proof test coverage is archived — do not load it unless asked. Run commands remain in [`TESTING.md`](../TESTING.md).
10. Milestone 5 inventory API is archived — do not load [`archive/2026-09-18-inventory-api/`](archive/2026-09-18-inventory-api/) unless asked. Durable notes: [`implementation-memory/inventory-api.md`](implementation-memory/inventory-api.md).
11. Milestone 5 Part 2 inventory UI is archived — do not load [`archive/2026-09-18-inventory-backoffice-ui/`](archive/2026-09-18-inventory-backoffice-ui/) unless asked. Durable notes: [`implementation-memory/inventory-backoffice-ui.md`](implementation-memory/inventory-backoffice-ui.md).
12. Docker Compose (`infra-40`) is archived — do not load [`archive/2026-09-23-docker-compose/`](archive/2026-09-23-docker-compose/) unless asked. Durable notes: [`implementation-memory/docker-compose-dev.md`](implementation-memory/docker-compose-dev.md). This ticket **adds** redis/worker/flower without replacing `ui`/`backend`.
13. Web Vitals is archived — do not load [`archive/2026-09-23-web-vitals/`](archive/2026-09-23-web-vitals/) unless asked. Durable notes: [`implementation-memory/web-vitals.md`](implementation-memory/web-vitals.md). Evidence remains in root `AUDIT.md`, `REPORT.md`, and `audit/`.
14. Backend serialization is archived — do not load [`archive/2026-09-24-serialization/`](archive/2026-09-24-serialization/) unless asked. Durable notes: [`implementation-memory/serialization-audit.md`](implementation-memory/serialization-audit.md). Trail remains in [`docs/serialization-audit.md`](../docs/serialization-audit.md). New routes must be added to `JSON_ROUTES` only; do not rewrite the historical audit.
15. Caching optimisation is archived — do not load [`archive/2026-09-30-caching-optimisation/`](archive/2026-09-30-caching-optimisation/) unless asked. Durable notes: [`implementation-memory/caching.md`](implementation-memory/caching.md). Trail remains in [`CACHING_REPORT.md`](../CACHING_REPORT.md). Inventory cache stays in-process TTL; Redis is not the app cache.
16. Telemetry is archived — do not load [`archive/2026-10-14-telemetry/`](archive/2026-10-14-telemetry/) unless asked. Durable notes: [`implementation-memory/telemetry.md`](implementation-memory/telemetry.md). Plans remain in [`docs/telemetry/`](../docs/telemetry/).
17. Data pipeline is archived — do not load [`archive/2026-10-21-data-pipeline/`](archive/2026-10-21-data-pipeline/) unless asked. Durable notes: [`implementation-memory/clinic-supply-pipeline.md`](implementation-memory/clinic-supply-pipeline.md). Design remains in [`data/pipelines/PIPELINE_DESIGN.md`](../data/pipelines/PIPELINE_DESIGN.md).
18. Background-processes (DEV-53) is archived — do not load [`archive/2026-11-04-background-processes/`](archive/2026-11-04-background-processes/) unless asked. Durable notes: [`implementation-memory/nightly-export.md`](implementation-memory/nightly-export.md). Plans remain in [`docs/pipelines/`](../docs/pipelines/). Do not replace the nightly scheduler with Celery Beat.
19. DEV-55 message queue is archived — do not load [`archive/2026-11-04-message-queue/`](archive/2026-11-04-message-queue/) unless asked. Durable notes: [`implementation-memory/message-queue.md`](implementation-memory/message-queue.md). Plan remains in [`docs/queues/`](../docs/queues/).
20. Sales forecast is archived — do not load [`archive/2026-11-05-sales-forecast-model/`](archive/2026-11-05-sales-forecast-model/) unless asked. Durable notes: [`implementation-memory/sales-forecast.md`](implementation-memory/sales-forecast.md). Results remain in [`docs/sales-forecast/`](../docs/sales-forecast/). Do not add ML deps to the API or incident-analyzer requirements.
21. Regression-model evaluation is archived — do not load [`archive/2026-11-07-regression-model-eval/`](archive/2026-11-07-regression-model-eval/) unless asked. The handoff is `regression-model-eval-context.md` in that folder. Durable notes stay in [`implementation-memory/sales-forecast.md`](implementation-memory/sales-forecast.md). The fit report remains [`data/eval/evaluation_report.md`](../data/eval/evaluation_report.md).
22. Knowledge helper is built. Signed-in `POST /knowledge/query` returns `{ "answer": "..." }` and still asks the writing model when the search finds nothing. Do not re-cut the corpus or overwrite `data/eval/evaluation_report.md` or `data/eval/sales_forecast/`.
23. Support-agent map is built. `POST /agent/query` is signed in and returns `{ "answer", "run_id" }`. An empty policy search uses a fixed honest sentence. Checkpoints and traces stay in local SQLite.
24. Incident lookup is built. The latest upload keeps safe incident rows, without `patient_id`. The agent map chooses policy search, one incident read, or both.
25. HealthCore tool door (this iteration): `mcps/healthcore-company-tools` exposes `get_incident_status` and `query_inventory`. Stock changes return `INVENTORY_READ_ONLY`. The agent incident step uses that door. No ticket create and no status change.

## Acceptance criteria

- [x] Required memory-bank files exist at `memory-bank/` root.
- [x] Completed iterations archived: `2026-07-29-monorepo-ai-frontend`, `2026-08-28-supplier-directory`, `2026-08-28-staff-auth`, `2026-08-31-error-handling`, `2026-09-04-bullet-proof`, `2026-09-18-inventory-api`, `2026-09-18-inventory-backoffice-ui`, `2026-09-23-docker-compose`, `2026-09-23-web-vitals`, `2026-09-24-serialization`, `2026-09-30-caching-optimisation`, `2026-10-14-telemetry`, `2026-10-21-data-pipeline`, `2026-11-04-background-processes`, `2026-11-04-message-queue`, `2026-11-05-sales-forecast-model`, `2026-11-07-regression-model-eval`.
- [x] Project `AGENTS.md` points at the global memory-bank file names.
- [x] AUTH-088 / API-042 / FE-019 implemented; results in [`TESTING.md`](../TESTING.md).
- [x] `BulletProofApp-Context.md` moved to `memory-bank/archive/2026-09-04-bullet-proof/`.
- [x] Milestone 5 inventory API: six authenticated `/inventory` routes, SQLModel persistence, seed, pytest, live `/docs` smoke; phase guide in `archive/2026-09-18-inventory-api/`.
- [x] Milestone 5 Part 2 inventory UI: four authenticated `/backoffice/inventory/...` views in `uis/web`; phase guide in `archive/2026-09-18-inventory-backoffice-ui/`.
- [x] infra-40 Compose stack: `ui` + `backend` on `healthcore_dev`; phase guide in `archive/2026-09-23-docker-compose/`.
- [x] Web Vitals audit: production Lighthouse loop on both Next apps; phase guide in `archive/2026-09-23-web-vitals/`.
- [x] Serialization audit: explicit FastAPI contracts; phase guide in `archive/2026-09-24-serialization/`; trail in [`docs/serialization-audit.md`](../docs/serialization-audit.md).
- [x] Caching optimisation: staff lazy-loads + inventory TTL cache; phase guide in `archive/2026-09-30-caching-optimisation/`; trail in [`CACHING_REPORT.md`](../CACHING_REPORT.md).
- [x] Telemetry sprint: capture, storage, report; phase guide in `archive/2026-10-14-telemetry/`; durable notes in [`implementation-memory/telemetry.md`](implementation-memory/telemetry.md).
- [x] Data pipeline sprints 1–3: design, Prefect ETL + `/reporting`, subflows + dashboard; phase guide in `archive/2026-10-21-data-pipeline/`; durable notes in [`implementation-memory/clinic-supply-pipeline.md`](implementation-memory/clinic-supply-pipeline.md).
- [x] DEV-53 nightly export: `scripts/nightly_export.py`, `app.jobs.job_runner`, `docs/pipelines/job_runs.sql`; phase guide in `archive/2026-11-04-background-processes/`; durable notes in [`implementation-memory/nightly-export.md`](implementation-memory/nightly-export.md).
- [x] DEV-55: Redis official image, port 6379, `noeviction`; API/worker/Flower share `REDIS_URL`.
- [x] DEV-55: `POST /reporting/pipeline-runs` returns `202` + `task_id` without executing ETL in the API process; warmed healthy-broker latency observed under 200 ms (37–67 ms; first cold POST 1402 ms).
- [x] DEV-55: independent worker; `GET /tasks/{task_id}` public states; retries with backoff; one durable DLQ row after exhaustion.
- [x] DEV-55: Flower on 5555; README start/stop; focused tests + live Redis/worker evidence (live SUCCESS vs warehouse unverified).
- [x] Sales forecast: `scripts/train_sales_forecast.py` loads the raw CSV, splits 2016–2023 / 2024–2025, trains RF, writes eval artifacts.
- [x] Sales forecast: lag/rolling features are causal; same-month visits and avg revenue per visit are not predictors.
- [x] Sales forecast: test metrics include MSE, MAE, RMSE, RMSE%, R², ranking Gini, residual K2, visits_count PSI; 80% interval; 2024–2025 plot.
- [x] Sales forecast: `tests/pipelines/` split unit test passes; focused feature/metric tests pass; training script run recorded.
- [x] Sales forecast: documentation states Game A, metric formulas, leakage rules, actual numbers, and a report-card conclusion.
- [x] Regression-model evaluation: handoff archived at `archive/2026-11-07-regression-model-eval/regression-model-eval-context.md`. Fit report remains `data/eval/evaluation_report.md`.
- [x] Knowledge helper code: four documents, separate `setup` / `embed` / `retrieve` / `generate_answer` / `query`, signed-in `POST /knowledge/query`, protected `/knowledge` page, mocked tests, and `docs/rag/rag-design.md`.
- [ ] Knowledge helper live score: model ids, vector size, minimum score, and Recall@3 of at least 80% after a real embedding model is configured.
- [x] Support-agent map: compiled graph, signed-in `POST /agent/query`, three pipeline evals, a checkpoint for the run id, and `data/eval/agent-trace-example.json`. Live model answers stay unverified until the 4Geeks settings exist.
- [x] Incident lookup: safe rows saved from the upload, a 3-second read, automatic routing, honest fallbacks, and routing evals. Live model answers stay unverified.
- [x] HealthCore tool door: incident read, stock read, read-only rejection, staff-token check, and the agent incident step uses the door. Playground and live model answers stay unverified.

## Interfaces / expected behavior (standing)

| Surface | Expected behavior |
|---------|-------------------|
| `uis/website` | Public corporate site; EN/ES via `hc_lang` cookie; enquiry form; brand blues; no auth |
| `uis/web` | Public `/login`, `/register`, `/forgot-password`, `/reset-password`; protected welcome, `/operations`, `/incidents`, `/suppliers`, `/knowledge`, `/backoffice/inventory/{products,orders,orders/inbound,orders/outbound}`, `/backoffice/reporting/monthly-clinic-supply-performance`, `/account/profile`, `/account/change-password` |
| `scripts/` | Phase 1 `analyze.py` + `incidents-healthcore.csv`; `nightly_export.py` (DEV-53); `train_sales_forecast.py` and `eval_sales_forecast.py` (isolated `scripts/sales_forecast` uv env) |
| `services/api` | Incidents + suppliers (TinyDB) + staff auth + inventory (SQLModel) + telemetry + reporting + JWT task status + knowledge helper. Login is `POST /auth/login`. `GET /health` public. Sensitive routes require bearer JWT. CORS from `CORS_ORIGINS` (default `http://localhost:3001`, `http://127.0.0.1:3001`). Public `POST /users` does not return email. Inventory catalogue GETs may be served from in-process TTL cache. Public `POST /telemetry/events`; `GET /telemetry/report` (60s cache). JWT `GET /reporting/...` for clinic-month KPIs and latest pipeline run. JWT `POST /reporting/pipeline-runs` enqueues Celery and returns `202 {"task_id"}`. JWT `GET /tasks/{task_id}` returns normalized Celery state. JWT `POST /knowledge/query` accepts `{ "question" }` and returns `{ "answer" }`. JWT `POST /agent/query` accepts `{ "question" }` and returns `{ "answer", "run_id" }`. |
| Compose | `docker compose up` from repo root: website 3000, staff UI 3001, API 8000, Redis 6379, Flower 5555 on network `healthcore_dev`. Worker is a separate process using `-A app.celery_app`. |
| Future `services/healthcore-api` | FastAPI `/api/v1` domains; OpenAPI contract for frontends |
| Agents | Skill discovery before non-trivial work; smallest change that satisfies the ask; no secrets; no git publish unless asked |

## Validation

- Code changes: follow requirement 6; report tests added/updated, commands run, results, and unverified risks.
- API: `uv run pytest` from `services/api`. Auth coverage: `uv run pytest --cov=app.auth`. Backoffice coverage: `--cov=app.routers.incidents --cov=app.routers.suppliers --cov=app.suppliers`. Inventory: `uv run pytest tests/test_inventory_products.py tests/test_inventory_orders.py tests/test_inventory_seed.py`. CORS: `uv run pytest tests/test_cors.py`. Cache: `uv run pytest tests/test_cache_inventory.py`. Queue: `uv run pytest tests/test_celery_app.py tests/test_dead_letter.py tests/test_pipeline_task.py tests/test_tasks_status.py tests/test_reporting.py`.
- Sales forecast: `uv --directory scripts/sales_forecast run pytest` (package tests + `tests/pipelines/test_sales_forecast_*.py`); then `uv --directory scripts/sales_forecast run python ../train_sales_forecast.py` and `uv --directory scripts/sales_forecast run python ../eval_sales_forecast.py`. Training notes stay in `docs/sales-forecast/sales-forecast.md`. The fit report is `data/eval/evaluation_report.md`.
- UI: `npm run typecheck`. Frontend helpers: `npm test -w uis/web`.
- Compose: `docker compose config`; `docker compose up --build`; host curls on 3000/3001/8000; Flower `http://localhost:5555`; `docker compose exec ui wget -qO- http://backend:8000/health`.
- Docs-only: confirm memory files present and `AGENTS.md` links resolve. No runtime test required.
- Real Resend delivery requires a local `RESEND_API_KEY` (not in git). Empty `DATABASE_URL` uses sqlite under `services/api/data/`.
- Optional one-time seed (system packages in the image, not host `.venv`): `docker compose exec backend python -m app.auth.seed` then `python -m app.inventory.seed`.
