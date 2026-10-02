# Storage implementation plan (telemetry-storage)

Frontend does not change. `TelemetryEvent` in [`schemas.py`](../../services/api/app/telemetry/schemas.py) is not modified.

## Table

Create `public.telemetry_events` (Supabase) with columns: `id` uuid PK default `gen_random_uuid()`, `timestamp` timestamptz NOT NULL, `service` text NOT NULL, `event_type` text NOT NULL, `level` text default `info`, `value` numeric null, `message` text null, `tags` jsonb default `{}`. Indexes on `timestamp`, `event_type`, GIN on `tags`. Application code never UPDATE/DELETE these rows.

Row mapping: `timestamp` ← event.timestamp; `service` = `backoffice`; `event_type` ← event.event_type; `level` from type (`frontend_error_raised` → `error`; login/session/reject → `warn`; else `info`); `value` from `properties.duration_ms` or `properties.quantity` if numeric; `message` null; `tags` = allowlisted properties plus envelope `eventId`, `sessionId`, `userId`, `schemaVersion`, `requestId`.

## Endpoint

Replace stub internals of `POST /telemetry/events`:

- Parse `{ "events": [...] }` as a list of raw dicts (not `list[TelemetryEvent]` on the body).
- `TelemetryEvent.model_validate(raw)` per item in try/except `ValidationError`.
- Bulk-insert valid rows in one PostgREST insert (or injected store in pytest).
- Return `{ received, stored, rejected }`. HTTP 200 if the envelope has `events`. Missing/non-list `events` → 422.

`TELEMETRY_ENDPOINT` unchanged. Tests patch the insert so CI does not need live Supabase credentials.
