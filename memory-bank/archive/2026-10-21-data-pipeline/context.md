# Context — HealthCore Digital (archived snapshot)

## Goal

Data-pipeline sprints 1–3 on branch `data-pipeline`. Phase guide: [`pipeline-context.md`](pipeline-context.md). Durable notes: [`implementation-memory/clinic-supply-pipeline.md`](../../implementation-memory/clinic-supply-pipeline.md).

## Scope (standing)

- Keep shipped UIs runnable: `uis/website` (public), `uis/web` (staff JWT, including inventory).
- Phase 1 incident CLI: [`scripts/`](../../../scripts/).
- Phase 2 API: incidents, suppliers, staff JWT auth, inventory, telemetry, reporting.
- Local stack: `docker compose up` starts website (3000), staff UI (3001), and FastAPI (8000).

## Constraints

- APIs live only under `services/`.
- No PHI in reporting tables, endpoints, logs, or dashboard.
- Do not change `GET /telemetry/report` or `app/telemetry/analysis.py`.
- Clinic ids `"1"`–`"12"`; cost = `unit_cost × quantity`; consumption is event count.

## Relevant files

| Path | Role |
|------|------|
| `pipeline-context.md` | Pipeline phase guide (this archive) |
| `data/pipelines/PIPELINE_DESIGN.md` | Monthly clinic supply performance design |
| `data/pipelines/pipeline.py` | Prefect ETL |
| `docs/pipelines/` | Sprint plans + `reporting.sql` |
| `uis/web/.../monthly-clinic-supply-performance/` | Board dashboard |
