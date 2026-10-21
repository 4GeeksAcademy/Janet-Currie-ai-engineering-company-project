# Decisions — Telemetry (archived snapshot)

## Adopted

| Decision | Rationale |
|----------|-----------|
| Telemetry `event_type` values come from HealthCore plan/schemas, not README placeholders | Capture assignment forbids generic names |
| Single public `track()`; ingest URL from `NEXT_PUBLIC_TELEMETRY_ENDPOINT` | Tech-lead: no scattered fetch; stub URL swappable later |
| Stub `POST /telemetry/events` is unauthenticated | `sendBeacon` cannot attach JWT; payloads are allowlisted and non-PII |
| Per-event `model_validate`; do not type the POST body as `list[TelemetryEvent]` | Invalid items must become `rejected`, not fail the whole batch with 422 |
| Bulk insert to `telemetry_events`; response `{received, stored, rejected}` | Storage assignment; pytest uses an injectable in-memory inserter |
| Report uses Pandas (`load → refine → to_datetime(utc=True) → groupby → agg`) | Course requires Pandas, not ad-hoc SQL in the handler |
| `GET /telemetry/report` cached 60s in-process via `TtlCache` | Cheap repeat reads; `report_cache.clear()` on process start |
| Opaque TinyDB `userId`; never email/password/PHI | HIPAA / UK GDPR |

## Rejected

| Alternative | Why rejected |
|-------------|--------------|
| Authenticated ingest | `sendBeacon` cannot attach JWT |
| Visual dashboard in this sprint | Optional; report API is sufficient |
| CEO conversion/revenue metrics | Out of scope for the technical report |
