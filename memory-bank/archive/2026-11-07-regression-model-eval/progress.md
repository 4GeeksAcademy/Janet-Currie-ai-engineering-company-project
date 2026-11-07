# Progress — Active iteration

## Current state

Archived 2026-11-07. Root `regression-model-eval-context.md` lives in this folder. The frozen forest is classified as overfitting. Do not stage it. The next change named in the report is a larger `min_samples_leaf` or a lower `max_depth`.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory backoffice UI, Docker Compose, Web Vitals, serialization, caching, telemetry, clinic-supply pipeline, nightly telemetry export, Redis/Celery message queue, sales-forecast feasibility (unsupported vs seasonal-naive).

## Completed (this iteration)

- Added training-period evaluation in `scripts/sales_forecast/sales_forecast/evaluation.py` and `scripts/eval_sales_forecast.py`.
- Wrote `data/eval/evaluation_report.md`, `data/eval/sales_forecast/cv_metrics.json`, and `data/eval/sales_forecast/learning_curve.png`.
- Diagnosis from the 2026-11-06 run: overfitting. Mean validation MAE is $150,009.95 ± $23,154.92. The 2022–2023 gap ratio is 0.74.

## Validation results

- `uv --directory scripts/sales_forecast run pytest` — 37 passed.
- `uv --directory scripts/sales_forecast run python ../eval_sales_forecast.py` — wrote the report, JSON, and learning curve. Report dollars match `cv_metrics.json`. The curve shows training MAE near $35k–$44k and validation MAE near $126k–$177k, with the gap still open at 72 training months.
- 2024–2025 are held out of the fold table. The prior holdout report card was not used as the verdict.

## Blockers

None.

## Next steps

1. Iteration closed. Do not commit or open a PR unless asked.

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

Last updated: 2026-11-06
