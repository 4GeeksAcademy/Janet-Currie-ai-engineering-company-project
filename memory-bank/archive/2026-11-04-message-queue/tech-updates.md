# Tech updates — Message queue (DEV-55)

- Celery app: [`services/api/app/celery_app.py`](../../../services/api/app/celery_app.py). Worker command `-A app.celery_app`. JSON serialization, `task_track_started`, UTC, `result_expires=86400`, `visibility_timeout=3600`, prefetch 1, concurrency 1.
- Producer: JWT `POST /reporting/pipeline-runs` returns `202 {"task_id"}` and `Location: /tasks/{task_id}`. Broker down is `503`. In-process HTTP 409 lock dropped.
- Worker task `app.tasks.pipeline_run.run_clinic_supply_pipeline` calls `execute_monthly_clinic_supply_performance`. Soft 840s / hard 900s. `max_retries=3` means four executions; backoff 5s/10s/20s. Exhaustion writes one `dead_letter_tasks` row (`attempt_number=4`).
- Status: JWT `GET /tasks/{task_id}` public states `pending | started | success | failure`.
- Compose: additive `redis:7.4.2-alpine` (`noeviction`, AOF `everysec`), `worker`, `flower` on `healthcore_dev`. Flower `FLOWER_UNAUTHENTICATED_API=true`.
- Tests: `test_celery_app.py`, `test_dead_letter.py`, `test_pipeline_task.py`, `test_tasks_status.py`; reporting POST expects `TaskAcceptedResponse`.
- Live SUCCESS against PostgREST was unverified (worker DNS `ConnectError`). Redis crash/AOF restart was not run.
- Durable notes: [`implementation-memory/message-queue.md`](../../implementation-memory/message-queue.md).
