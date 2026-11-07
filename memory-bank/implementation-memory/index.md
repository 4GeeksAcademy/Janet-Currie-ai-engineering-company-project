# Implementation memory catalog

| Implementation | Description | File | Keywords |
|----------------|-------------|------|----------|
| Bullet-proof test coverage | AUTH-088 / API-042 / FE-019 pytest and Jest suites | [bullet-proof-test-coverage.md](bullet-proof-test-coverage.md) | pytest, Jest, auth, incidents, suppliers, toUserMessage |
| Inventory API | HCR-0188 SQLModel `/inventory` catalogue and movements | [inventory-api.md](inventory-api.md) | SQLModel, MedicalSupply, current_stock, seed-inventory |
| Inventory backoffice UI | Authenticated `uis/web` supplies, delivery, consumption, history | [inventory-backoffice-ui.md](inventory-backoffice-ui.md) | /backoffice/inventory, InsufficientStockError, stockStatus |
| Docker Compose dev stack | Two-service `docker compose up` for website, staff UI, FastAPI | [docker-compose-dev.md](docker-compose-dev.md) | infra-40, healthcore_dev, CORS_ORIGINS, NEXT_PUBLIC_API_BASE_URL |
| Web Vitals audit | Production Lighthouse loop on `uis/website` and `uis/web` | [web-vitals.md](web-vitals.md) | Lighthouse, hc_lang, LangToggle, useAsyncResource |
| Serialization audit | Explicit FastAPI `response_model` contracts; no email on public register | [serialization-audit.md](serialization-audit.md) | UserRegisteredResponse, HealthResponse, IncidentAnalysisResponse, response_model |
| Caching optimisation | Staff `next/dynamic` islands + in-process TTL on inventory GETs | [caching.md](caching.md) | TtlCache, REQUEST_TIMING, deriveMovementRows, INVENTORY_LOAD_EXTRA |
| Telemetry | Capture queue, Supabase bulk insert, operational report | [telemetry.md](telemetry.md) | track, TelemetryEvent, telemetry_events, GET /telemetry/report |
| Clinic supply pipeline | Prefect subflows, JWT `/reporting`, staff dashboard | [clinic-supply-pipeline.md](clinic-supply-pipeline.md) | unit_cost, monthly_clinic_supply_performance, execute_monthly_clinic_supply_performance |
| Nightly telemetry export | OS-process CSV backup + pipeline subprocess (`job_runs`) | [nightly-export.md](nightly-export.md) | nightly_export, TARGET_DATE, reporting.job_runs |
| Async task queue | Redis + Celery worker for `POST /reporting/pipeline-runs` | [message-queue.md](message-queue.md) | REDIS_URL, Celery, Flower, dead_letter_tasks |
| Sales forecast | Rolling one-month-ahead RF feasibility and training-period fit evaluation | [sales-forecast.md](sales-forecast.md) | revenue_usd, MAE, learning curve, overfitting, seasonal-naive |
