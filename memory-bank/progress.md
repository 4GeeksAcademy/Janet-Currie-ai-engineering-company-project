# Progress — Active iteration

## Current state

No active implementation ticket. Phase guides archived:

- DEV-55 message queue → [`archive/2026-11-04-message-queue/`](archive/2026-11-04-message-queue/)
- Sales forecast → [`archive/2026-11-05-sales-forecast-model/`](archive/2026-11-05-sales-forecast-model/)

Root `message-queue-context.md`, `sales-forecast-model-context.md`, and `healthcore-BRIEFING.en.md` were removed after the copies were archived.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory backoffice UI, Docker Compose, Web Vitals, serialization, caching, telemetry, clinic-supply pipeline, nightly telemetry export, Redis/Celery message queue, sales-forecast feasibility (unsupported vs seasonal-naive).

## Completed (this iteration)

- Archived the message-queue, sales-forecast, and HealthCore briefing phase documents.

## Validation results

Archival only (docs/memory). No runtime tests required.

## Blockers

None.

## Next steps

1. Wait for the next sprint. Do not open a PR unless asked.

## Run commands (durable)

```bash
uv sync --directory scripts/sales_forecast --group dev
uv --directory scripts/sales_forecast run pytest
uv --directory scripts/sales_forecast run python ../train_sales_forecast.py
cd services/api && uv run pytest
python3 data/pipelines/pipeline.py
./services/api/.venv/bin/python scripts/nightly_export.py
docker compose up --build
```

Last updated: 2026-11-05
