# Spec — Data pipeline (archived snapshot)

## Requirements

- Sprint 1: [`data/pipelines/PIPELINE_DESIGN.md`](../../../data/pipelines/PIPELINE_DESIGN.md); inbound `unit_cost`.
- Sprint 2: Prefect ETL; JWT `/reporting` routes.
- Sprint 3: subflows; `tests/pipelines/test_pipeline.py`; dashboard at `/backoffice/reporting/monthly-clinic-supply-performance`.

## Acceptance criteria

- [x] Sprint 1 design + `unit_cost` capture.
- [x] Sprint 2 pipeline + three `/reporting` endpoints.
- [x] Sprint 3 subflows, isolated tests, dashboard.
- [x] Phase guide moved to this archive.

## Interfaces

JWT `GET /reporting/monthly-clinic-supply-performance`, `GET /reporting/pipeline-runs/latest`, `POST /reporting/pipeline-runs`. Dashboard fetches the KPI endpoint only. USD and GBP stay separate.
