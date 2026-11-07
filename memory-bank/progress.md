# Progress — Active iteration

## Current state

No active implementation ticket. Regression-model evaluation is archived at [`archive/2026-11-07-regression-model-eval/`](archive/2026-11-07-regression-model-eval/). Root `regression-model-eval-context.md` was moved there. The fit report remains `data/eval/evaluation_report.md`.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory backoffice UI, Docker Compose, Web Vitals, serialization, caching, telemetry, clinic-supply pipeline, nightly telemetry export, Redis/Celery message queue, sales-forecast feasibility (unsupported vs seasonal-naive), regression-model evaluation (overfitting; do not stage).

## Completed (this iteration)

- Archived the regression-model evaluation handoff and the closing memory snapshot under `archive/2026-11-07-regression-model-eval/`.

## Validation results

Archive only. The evaluation checks from 2026-11-06 stay recorded in the archive `progress.md`. No new runtime tests were required to move the handoff.

## Blockers

None.

## Next steps

1. Wait for the next sprint. Do not open a PR unless asked.

## Run commands (durable)

```bash
uv sync --directory scripts/sales_forecast --group dev
uv --directory scripts/sales_forecast run pytest
uv --directory scripts/sales_forecast run python ../train_sales_forecast.py
uv --directory scripts/sales_forecast run python ../eval_sales_forecast.py
cd services/api && uv run pytest
python3 data/pipelines/pipeline.py
./services/api/.venv/bin/python scripts/nightly_export.py
docker compose up --build
```

Last updated: 2026-11-07
