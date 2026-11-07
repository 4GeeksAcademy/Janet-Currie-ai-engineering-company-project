# Context — HealthCore Digital (archived snapshot)

## Goal

DEV-55 Redis + Celery + Flower on branch `background-processes` (no separate `message-queue` branch). Phase guide: [`message-queue-context.md`](message-queue-context.md). Durable notes: [`implementation-memory/message-queue.md`](../../implementation-memory/message-queue.md).

## Scope (standing)

- Keep shipped UIs runnable: `uis/website` (public), `uis/web` (staff JWT, including inventory).
- Phase 1 incident CLI: [`scripts/`](../../../scripts/).
- Phase 2 API: incidents, suppliers, staff JWT auth, inventory, telemetry, reporting, Celery queue.
- Local stack: `docker compose up` starts website (3000), staff UI (3001), FastAPI (8000), Redis (6379), worker, Flower (5555).

## Constraints

- Celery module is `app.celery_app`, not `services.celery_app`.
- Redis is broker/result only; inventory cache stays in-process TTL.
- Nightly/`job_runs` stay on OS cron, not Celery Beat.
- Do not `load_dotenv` at Celery import time.

## Relevant files

| Path | Role |
|------|------|
| `message-queue-context.md` | DEV-55 phase guide (this archive) |
| `docs/queues/message-queue-implementation-plan.md` | Execution plan |
| `services/api/app/celery_app.py` | Celery application |
| `services/api/app/tasks/` | Pipeline task + DLQ |
| `services/api/app/routers/reporting.py` | 202 producer |
| `services/api/app/routers/tasks.py` | `GET /tasks/{task_id}` |
