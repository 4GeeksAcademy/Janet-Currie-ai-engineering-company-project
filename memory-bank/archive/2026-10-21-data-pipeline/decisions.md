# Decisions — Data pipeline (archived snapshot)

Standing pipeline decisions remain in the active [`decisions.md`](../../decisions.md). Highlights:

- Prefect `>=3` via `uv` in `services/api`.
- HTTP/CLI/tests use `execute_monthly_clinic_supply_performance` (`task.fn()`), not `@flow()`.
- Reporting warehouse is PostgREST `reporting` schema.
- Dashboard is `uis/web` `/backoffice/reporting/...` (no `uis/backoffice` app).
- Currency from `country` only; clinic ids `"1"`–`"12"`.
