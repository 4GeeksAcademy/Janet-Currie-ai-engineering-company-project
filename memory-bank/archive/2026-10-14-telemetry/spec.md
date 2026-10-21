# Spec — Telemetry (archived snapshot)

## Requirements

Capture HealthCore-named staff events via one `track()` queue; persist valid batches; serve a cached operational Pandas report. No PII/PHI. Staff UI is `uis/web`. APIs stay under `services/api`.

## Acceptance criteria

- [x] `Telemetry-Context.md` at repo root on branch `telemetry` (now archived here).
- [x] Capture: stub ingest, TelemetryService, mandatory + technical baseline events, no PII.
- [x] Storage: per-event validate, bulk insert, `{received,stored,rejected}`; frontend unchanged.
- [x] Report: three-plus Pandas operational metrics, `GET /telemetry/report`, 60s cache.

## Validation

- Capture: pytest 118 passed; focused Jest 26; typecheck/lint web.
- Storage: focused 14 passed; full pytest 122 passed.
- Report: focused 17 passed; full pytest **125 passed**.
- Live Supabase `telemetry_events` DDL not applied (MCP timeout); SQL in `docs/telemetry/telemetry_events.sql`.
