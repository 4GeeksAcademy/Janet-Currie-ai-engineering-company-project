# Progress — Active iteration

## Current state

DEV-55 message queue is implemented. Plan: [`docs/queues/message-queue-implementation-plan.md`](../docs/queues/message-queue-implementation-plan.md). Operator notes: [`docs/queues/message-queue.md`](../docs/queues/message-queue.md). Do not push or open a PR unless asked.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory backoffice UI, Docker Compose, Web Vitals, serialization, caching, telemetry, clinic-supply pipeline, nightly telemetry export.

## Completed (this iteration)

- Redis + Celery + Flower on Compose; `app.celery_app`; JWT `POST /reporting/pipeline-runs` → `202`; `GET /tasks/{task_id}`; SQLModel `dead_letter_tasks`; focused tests; live Compose evidence.

## Validation results

- Focused pytest: **40 passed, 1 skipped**, then Redis integration **passed**.
- Full `uv run pytest`: **195 passed, 1 skipped** (2026-11-04).
- `docker compose config` resolves redis/worker/flower.
- Live Compose (2026-11-04): Redis healthy; worker registered `run_clinic_supply_pipeline`; Flower `:5555` HTML 200; five warmed `202`s 37–67 ms (cold first 1402 ms); poll pending→started→failure; retries 5s/10s/20s; five DLQ rows `attempt_number=4`; worker continued with API stopped; queue `LLEN=1` while worker down then received after restart.
- Live SUCCESS against PostgREST **unverified** (worker `ConnectError: Name or service not known`). Redis crash/AOF restart **not run**. Live KPI redelivery **unverified**. `job_runs.sql` still not live-applied; crontab not installed (DEV-53, unrelated).

## Blockers

None.

## Next steps

1. Wait for the user to request a commit (and a `message-queue` branch if they want git separated from `background-processes`).
2. Optional: live SUCCESS once worker can resolve the reporting warehouse.

## Run commands (durable)

```bash
cd services/api && uv run pytest
python3 data/pipelines/pipeline.py
./services/api/.venv/bin/python scripts/nightly_export.py
docker compose up --build
```

Last updated: 2026-11-04
