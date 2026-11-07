# DEV-55 implementation plan — async task queue

Ticket **#DEV-55**. Branch target: `message-queue` (from the DEV-53 tip). Contract: [`message-queue-context.md`](../../message-queue-context.md).

Approved 2026-11-04: Redis as Celery broker/result only; Celery module `app.celery_app`; convert JWT `POST /reporting/pipeline-runs`; SQLModel `dead_letter_tasks` on existing `DATABASE_URL`; additive Compose `redis` / `worker` / `flower`; in-process inventory cache unchanged; nightly/`job_runs`/`pipeline_runs` unchanged.

This file is the execution record. Git branch/commit/push/PR only when the user authorizes them.

## Current inspected state

- FastAPI package is `app` under `services/api`. Image WORKDIR `/app/services/api`. Copies/mounts: `services/api`, `scripts`, `data/pipelines`.
- Compose is `ui` + `backend` on `healthcore_dev`. No Redis, Celery, Flower, or `REDIS_URL`.
- Caching is in-process `TtlCache`, not Redis.
- No Alembic. Inventory uses SQLModel `create_all`. Warehouse SQL is applied manually.
- JWT `POST /reporting/pipeline-runs` runs `execute_monthly_clinic_supply_performance` inline and returns `200 PipelineRunResponse`. Staff UI only GETs `/reporting/pipeline-runs/latest`.
- Nightly export is `scripts/nightly_export.py` + `reporting.job_runs`. Independent of this ticket.
- Pytest lives under `services/api` (`uv run pytest`). `helpers.py` forces temp SQLite and pops live `SUPABASE_*`.

## Selected operation

**Convert:** `POST /reporting/pipeline-runs`.

Stay synchronous: `/health` and CRUD (cheap or request-bound); `GET /telemetry/report` (public, 60s cache); `POST /api/incidents/analyze` (interactive upload, no batch ID); nightly CLI (not an API producer).

Baseline timings are recorded in this file after the measurement step. Time limits start at soft 840s / hard 900s (align with nightly subprocess timeout) unless measurement says otherwise.

## Producer contract

| Before | After |
|--------|--------|
| `200` `PipelineRunResponse` after ETL | `202` `{"task_id": "<uuid>"}` (`TaskAcceptedResponse`) |
| — | `Location: /tasks/{task_id}` |
| HTTP `409` from in-process `pipeline_lock` | Dropped at HTTP layer. KPI upsert `(clinic_id, month_start)` is the durable idempotency. |
| Invalid `month_start` `400`; missing JWT `401` | Unchanged, no enqueue |
| Broker down / missing `REDIS_URL` at publish | `503`, no fake `202` |

Worker payload: `month_start` ISO date or `null` only. Safe Redis result: `{run_id, status, month_start, records_processed, events_extracted, events_quarantined}`. Failure public `result` is `null`.

Celery `max_retries=3` = **4 executions** (attempt = `retries + 1`). Do not set `max_retries=2`.

## Files to add or change

| Path | Action |
|------|--------|
| `services/api/app/celery_app.py` | Celery app; `-A app.celery_app` |
| `services/api/app/tasks/` | DLQ model/store, pipeline task, status helpers |
| `services/api/app/routers/tasks.py` | JWT `GET /tasks/{task_id}` |
| `services/api/app/routers/reporting.py` | POST becomes 202 producer |
| `services/api/app/reporting/schemas.py` | `TaskAcceptedResponse`, `TaskStatusResponse` |
| `services/api/app/database.py` | `create_all` includes DLQ model |
| `services/api/app/main.py` | include tasks router |
| `docker-compose.yml` | add `redis`, `worker`, `flower` |
| `services/api/pyproject.toml`, `requirements.txt`, `uv.lock` | celery, redis, flower |
| `.env.example`, `services/api/.env.example` | `REDIS_URL` comments |
| `services/api/tests/helpers.py` | force test `REDIS_URL` |
| `services/api/tests/test_*.py` | celery, reporting, status, task, DLQ |
| `README.md`, `services/api/README.md`, `TESTING.md` | operator/test commands |
| `docs/queues/message-queue.md` | operator notes + evidence template |
| `memory-bank/{context,spec,progress,decisions}.md` | active iteration |

Do **not** edit: `src/types/**`, `src/utils/**`, `CONTEXT.md`, nightly script, `job_runs`, ETL copy, inventory cache, `uis/web` dashboard, `memory-bank/archive/`.

## Celery / Redis values

- Broker and result: `REDIS_URL` (`redis://redis:6379/0` in Compose; `redis://localhost:6379/0` on host).
- JSON serializers only. `task_track_started=True`. UTC.
- `result_expires=86400`. `visibility_timeout=3600`.
- Worker `--concurrency=1`, `worker_prefetch_multiplier=1`.
- `task_reject_on_worker_lost=False`. `acks_late=True` on the pipeline task.
- Backoff: `countdown = min(60, 5 * 2 ** retries)` → 5s, 10s, 20s.
- Redis image `redis:7.4.2-alpine`, `maxmemory 256mb`, `noeviction`, AOF `everysec`, volume `redis_data`.

## Status mapping

| Celery | Public |
|--------|--------|
| PENDING, RECEIVED | pending |
| STARTED, RETRY | started |
| SUCCESS | success |
| FAILURE, REVOKED | failure |

Unknown/expired IDs are `pending` after JWT. No per-user task registry (reporting is already any-staff).

## DLQ

SQLModel table `dead_letter_tasks` on inventory `DATABASE_URL`. Unique `task_id`. Fields: `id`, `task_id`, `task_name`, `attempt_number`, sanitized `error_message` (cap 400), `failed_at`, `created_at`. Operator SQL at `services/api/app/tasks/schema.sql`. No Alembic. No broker dead-letter queue. No replay endpoint.

## Measurement baseline

Recorded 2026-11-04 with `uv run pytest --durations=20` on isolated TestClient data (`tests/test_reporting.py`, `tests/test_incidents_api.py`). Per-test times include auth/register overhead (~1s), so they are not raw handler latency.

| Check | Representative duration | Queue-appropriate? |
|-------|-------------------------|--------------------|
| `test_latest_run_404_then_post_and_get` (includes current sync POST ETL on fake store) | 1.29s | Yes — live PostgREST extract/load is the slow path; fake store hides warehouse I/O |
| `test_empty_kpi_get_is_200` | 1.75s | No — read path; staff dashboard already polls GET |
| `test_analyze_graded_fixture` | 1.22s | No — interactive CSV upload; no batch ID |
| `test_health` | 1.03s | No — liveness |
| Inventory catalogue (prior cache profile) | ~106 ms miss | No — already TTL-cached; mutating/request-bound |

**Selected:** `POST /reporting/pipeline-runs`. It is the only JWT route that still runs the clinic-supply ETL in the request. Live warehouse duration can exceed the 200 ms producer budget; isolated fakes cannot. Incident analyze stays synchronous (upload UX). Telemetry report stays synchronous (public, 60s cache). Time limits remain soft 840s / hard 900s to match nightly.

## Validation

```bash
uv --directory services/api run pytest tests/test_celery_app.py tests/test_dead_letter.py tests/test_pipeline_task.py tests/test_tasks_status.py tests/test_reporting.py
uv --directory services/api run pytest
docker compose config
```

Live Compose scenarios (observe, do not infer) are listed in [`message-queue.md`](message-queue.md).
