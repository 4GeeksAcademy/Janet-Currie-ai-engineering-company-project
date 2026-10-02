# Telemetry (capture, storage, report)

## Purpose

Capture staff-app usage as HealthCore-named events, persist valid batches, and serve a technical operations report.

## Final Behavior

- `track()` in `uis/web` queues events (10s / 20) and posts to `NEXT_PUBLIC_TELEMETRY_ENDPOINT`. Envelope fields are generated in the service. No email/password/PHI.
- `POST /telemetry/events` validates each item with unchanged `TelemetryEvent`, bulk-inserts valid rows, returns `{received, stored, rejected}`.
- `GET /telemetry/report` returns `{period, metrics}` for a UTC window (default 7 days) from Pandas functions, cached 60s.

## Important Files

- `docs/telemetry/telemetry-plan.md`, `event-schemas.json`
- `uis/web/src/lib/telemetry.ts`
- `services/api/app/telemetry/schemas.py`, `store.py`, `analysis.py`
- `services/api/app/routers/telemetry.py`
- `docs/telemetry/telemetry_events.sql`

## Decisions and Constraints

- Staff UI is `uis/web`. Event names from HealthCore plan, not README generics.
- Stub URL env vars stay so storage/report do not change the frontend ingest path.
- Live Supabase DDL may need manual apply (`telemetry_events.sql`) if MCP times out.

## Validation

Capture pytest 118; storage 122; report full suite **125 passed**. Live Supabase DDL not applied (MCP timeout).
