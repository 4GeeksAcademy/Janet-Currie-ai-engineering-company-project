# Tech updates — Telemetry

- Envelope: `eventId`, `timestamp`, `sessionId`, `userId` (opaque TinyDB id or `anonymous`), `event_type`, `schemaVersion`, `requestId`, `properties` (allowlist only).
- Staff `uis/web` `track()` queues 10s or 20 events, `sendBeacon` with fetch fallback, retry/backoff. Ingest URL: `NEXT_PUBLIC_TELEMETRY_ENDPOINT`.
- `POST /telemetry/events` is public; each item is `TelemetryEvent.model_validate`; extra fields forbidden.
- Storage: `event_to_row` + injectable `supabase_insert` (PostgREST). DDL: [`docs/telemetry/telemetry_events.sql`](../../../docs/telemetry/telemetry_events.sql).
- Report: `events_per_day`, `error_rate_by_type`, `latency_by_day`, `auth_failure_rate` in `app/telemetry/analysis.py`; `GET /telemetry/report` TTL 60s.
- pandas added to `pyproject.toml` / `requirements.txt` / `uv.lock`.
- Durable notes: [`implementation-memory/telemetry.md`](../../implementation-memory/telemetry.md).
