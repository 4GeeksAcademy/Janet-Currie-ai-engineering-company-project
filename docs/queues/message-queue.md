# DEV-55 — Redis / Celery operator notes

Contract: [`../../memory-bank/archive/2026-11-04-message-queue/message-queue-context.md`](../../memory-bank/archive/2026-11-04-message-queue/message-queue-context.md). Plan: [`message-queue-implementation-plan.md`](message-queue-implementation-plan.md).

## Topology

- Compose services: existing `ui` + `backend`, plus `redis`, `worker`, `flower` on `healthcore_dev`.
- Celery `-A` target: `app.celery_app` (WORKDIR `/app/services/api`). Not `services.celery_app`.
- Broker/result: `REDIS_URL`. Compose: `redis://redis:6379/0`. Host: `redis://localhost:6379/0`.
- Inventory cache stays in-process TTL. Redis is not an application cache.
- Nightly `scripts/nightly_export.py` and `job_runs` are unchanged. Domain `pipeline_runs` is unchanged.

## Attempt convention

Celery `max_retries=3` allows **four executions**: attempt_number = `retries + 1`. Backoff countdown is `min(60, 5 * 2 ** retries)` → 5s, 10s, 20s. DLQ `attempt_number` is 4 on retry exhaustion (or 1 on permanent input errors).

## Timeouts and retention

- Soft 840s / hard 900s (aligned with nightly subprocess timeout).
- Visibility timeout 3600s. Result expiry 24h. After expiry, `GET /tasks/{id}` looks `pending`.
- Worker `--concurrency=1`, prefetch 1. `acks_late=True`. `task_reject_on_worker_lost=False`.
- Redis: `redis:7.4.2-alpine`, `maxmemory 256mb`, `noeviction`, AOF `everysec`, volume `redis_data`. Worker downtime does not drop queued messages. Do not claim zero-loss across Redis crashes. `noeviction` plus a memory ceiling means new writes fail when full.

## Public contracts

`POST /reporting/pipeline-runs` (JWT): validates `month_start`, publishes `{month_start}`, returns `202 {"task_id"}` and `Location: /tasks/{task_id}`. Broker failure is `503`. Invalid month is `400` (no enqueue). In-process pipeline lock is not an HTTP 409.

`GET /tasks/{task_id}` (JWT): Celery `AsyncResult` mapped to `pending | started | success | failure`. Success `result` is `{run_id, status, month_start, records_processed, events_extracted, events_quarantined}`. Failure `result` is `null`. Unknown/expired IDs are `pending` after auth.

KPI upsert `(clinic_id, month_start)` is the durable idempotency for redelivery. Multiple `pipeline_runs` rows may exist.

DLQ table `dead_letter_tasks` on `DATABASE_URL` (sqlite `services/api/data/inventory.sqlite` when unset). Operator SQL: [`../../services/api/app/tasks/schema.sql`](../../services/api/app/tasks/schema.sql).

```sql
SELECT task_id, task_name, attempt_number, error_message, failed_at
FROM dead_letter_tasks
ORDER BY failed_at DESC;
```

## Start / stop

See root [`README.md`](../../README.md). Graceful: `docker compose stop worker` then `docker compose down`. Never `kill -9`. Flower `http://localhost:5555` is local demo only; Compose sets `FLOWER_UNAUTHENTICATED_API=true`. Do not expose Flower publicly.

## Live validation evidence

Observed 2026-11-04 on local Compose (no production data).

| # | Scenario | Command / observation | Result |
|---|---------|------------------------|--------|
| 1 | Redis healthy; worker registers task; Flower up | `docker compose up --build -d redis backend worker flower` (2026-11-04) | Redis healthy, worker `ready` with `run_clinic_supply_pipeline`, Flower HTML 200 on `:5555` |
| 2 | Producer `202` under 200 ms | JWT POST `/reporting/pipeline-runs` × 5 | All `202`. Times ms: 1402 (cold), 43, 37, 63, 67. Warmed min 37 / median 63. |
| 3 | Poll pending → started → terminal | `GET /tasks/{id}` | Observed `pending` then `started`. Terminal live state was `failure` (`result` null) because PostgREST host DNS failed in the worker (`ConnectError: Name or service not known`). Pytest success path with fake execute passed. |
| 4 | Stop API after enqueue; worker continues | `docker compose stop backend` after `202` for `34694472-…` | Worker received the task and retried (5s then 10s) while API was down (`curl` connection refused). |
| 5 | Stop worker, enqueue, restart, resume | `docker compose stop worker`; POST `202`; `LLEN celery` = 1; `docker compose start worker` | Worker log: task `a14bf38e-…` **received** after restart. |
| 6 | Transient retry backoff | Live ConnectError | Same `task_id`: Retry in **5s**, **10s**, **20s** (attempts 1–3) then attempt 4 failure. |
| 7 | Exhaustion: public failure + one DLQ row | SQLModel `dead_letter_tasks` | Five unique `task_id`s, each `attempt_number=4`. `GET /tasks/eade0a9d-…` → `{"status":"failure","result":null}`. |
| 8 | Flower | `http://localhost:5555` | Workers dashboard 200. After `FLOWER_UNAUTHENTICATED_API=true`, `/api/tasks` showed `FAILURE` and `RECEIVED`. No live SUCCESS (warehouse unreachable). |
| 9 | Redelivery vs KPI upsert | Live extract never committed | Unverified live. Domain upsert still the designed idempotency; pytest execute-once covered. |
| 10 | Redis restart | Not run | Unverified. Config observed: `maxmemory-policy=noeviction`, `appendonly=yes`. |
| 11 | Stop | `docker compose stop worker flower` after evidence | Worker warm shutdown logged earlier (`Warm shutdown`). |

## Troubleshooting

- Worker import errors: confirm `-A app.celery_app` and `data/` on `sys.path` (set in `celery_app.py`).
- Broker connection refused inside a container: `REDIS_URL` used `localhost` instead of `redis`.
- Stale `pending`: result expired (`result_expires=86400`) or unknown id (Celery default).
- FastAPI starts without a worker; missing `REDIS_URL` at publish is HTTP `503`.
