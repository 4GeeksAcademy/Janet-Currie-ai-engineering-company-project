# Async task queue (DEV-55)

## Purpose

Queue JWT `POST /reporting/pipeline-runs` through Redis and an independent Celery worker so the API returns `202` without running the clinic-supply ETL in-request.

## Final Behavior

- Producer: JWT `POST /reporting/pipeline-runs` validates `month_start`, publishes `{month_start}`, returns `202 {"task_id"}` and `Location: /tasks/{task_id}`. Broker failure is `503`.
- Worker: `celery -A app.celery_app worker --concurrency=1` calls `execute_monthly_clinic_supply_performance`.
- Status: JWT `GET /tasks/{task_id}` maps Celery states to `pending | started | success | failure`. Failure `result` is null.
- Retries: `max_retries=3` (four executions); backoff 5s / 10s / 20s. Exhaustion writes one `dead_letter_tasks` row (`attempt_number=4`).
- Flower on host port 5555 (local demo). Inventory cache stays in-process TTL.

## Architecture and Data Flow

Client → FastAPI producer → Redis (`REDIS_URL`, db 0) → Celery worker → existing ETL → PostgREST reporting tables. DLQ is SQLModel on `DATABASE_URL`. Nightly/`job_runs`/`pipeline_runs` remain separate.

## Important Files

- `services/api/app/celery_app.py`
- `services/api/app/tasks/`
- `services/api/app/routers/reporting.py`, `services/api/app/routers/tasks.py`
- `docker-compose.yml` (`redis`, `worker`, `flower`)
- `docs/queues/message-queue.md`

## Interfaces and Contracts

- Compose: `REDIS_URL=redis://redis:6379/0`. Host: `redis://localhost:6379/0`.
- Redis image `redis:7.4.2-alpine`, `noeviction`, AOF `everysec`.
- Soft 840s / hard 900s. Result expiry 24h. Visibility timeout 3600s.

## Decisions and Constraints

- Celery module is `app.celery_app`, not `services.celery_app`.
- HTTP 409 from in-process pipeline lock dropped; KPI upsert is redelivery safety.
- No Alembic; no Celery Beat; no cache-on-Redis.

## Validation

`uv run pytest` **195 passed, 1 skipped** then Redis integration **passed**. Live Compose (2026-11-04): warmed producer 37–67 ms `202`; pending→started→failure; retries 5/10/20s; five DLQ rows; worker continued with API down; queued message resumed after worker restart. Live SUCCESS against PostgREST unverified (worker DNS `ConnectError`).

## Maintenance Notes

Do not point the inventory `TtlCache` at Redis. Keep worker independent of `backend`. Flower is unauthenticated in Compose; do not publish it.
