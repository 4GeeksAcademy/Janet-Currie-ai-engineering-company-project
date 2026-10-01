# Report implementation plan (telemetry-report)

Technical report only (volume, errors, latency, auth failure rate). No CEO conversion/revenue metrics. Frontend capture/storage clients stay as they are except we add no required UI (dashboard is optional and skipped).

## Pipeline

[`services/api/app/telemetry/analysis.py`](../../services/api/app/telemetry/analysis.py):

- `events_per_day` — count of events by date and `event_type`.
- `error_rate_by_type` — share of `level == error` (or `frontend_error_raised`) by day and type.
- `latency_by_day` — mean `value` for `api_latency_recorded` by day.
- `auth_failure_rate` — `user_login_failed / (failed + succeeded)` by day (SQL `event_type IN (...)`).

Each function receives `start_date`/`end_date` (inclusive start, exclusive end, UTC), loads only needed rows (injectable loader for tests), refines tags in Pandas, `pd.to_datetime(..., utc=True)` before groupby, aggregates with Pandas (no Python metric loops), returns `list[dict]`.

## Endpoint

`GET /telemetry/report?start_date=&end_date=` defaults to last 7 days UTC. Resolves the window once and passes it into every metric. JSON `{ period: { from, to }, metrics: { ... } }`. In-memory TTL 60s keyed by the window (reuse `TtlCache`).

## Tests

Fake loader DataFrames: empty window, mixed types, string timestamps that need utc conversion, cache hit skips reload.
