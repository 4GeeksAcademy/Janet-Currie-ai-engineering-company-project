# Implementation plan — Telemetry

Three sequential phases, each on its own branch, each with a detailed plan only when that phase started:

1. **Capture** (`telemetry-capture`) — HealthCore event catalogue, one `track()` queue, stub `POST /telemetry/events`. Plan: [`docs/telemetry/capture-implementation-plan.md`](../../../docs/telemetry/capture-implementation-plan.md).
2. **Storage** (`telemetry-storage`) — per-event validate, bulk insert, `{received, stored, rejected}`. Plan: [`docs/telemetry/storage-implementation-plan.md`](../../../docs/telemetry/storage-implementation-plan.md).
3. **Report** (`telemetry-report`) — Pandas operational metrics, `GET /telemetry/report`, 60s cache. Plan: [`docs/telemetry/report-implementation-plan.md`](../../../docs/telemetry/report-implementation-plan.md).

Staff UI is `uis/web`. APIs stay in `services/api`. No PII/PHI. No Redis/CDN. Do not recount website `AppointmentModal`.
