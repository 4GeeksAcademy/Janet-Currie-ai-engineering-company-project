# Capture implementation plan (telemetry-capture)

Contract source: [`Telemetry-Context.md`](../../Telemetry-Context.md) plus this file and [`event-schemas.json`](event-schemas.json). There is no prior approved plan in-repo; HealthCore names below are the catalogue (not README placeholders).

Staff UI is `uis/web`. APIs stay in `services/api`. Stub does **not** write a database.

## Backend

- New router `POST /telemetry/events` (public, so `sendBeacon` works without JWT).
- Body `{ "events": [TelemetryEvent, ...] }` with envelope fields: `eventId`, `timestamp`, `sessionId`, `userId`, `event_type`, `schemaVersion`, `requestId`, `properties`.
- Log count + each `event_type`. Return `{ "received": N }`.
- Read `TELEMETRY_ENDPOINT` at import (default `http://localhost:8000/telemetry/events`) to establish the env pattern; do not proxy.
- Add `JSON_ROUTES` row. CORS already allows `:3001`.

## Frontend

- [`uis/web/src/lib/telemetry.ts`](../../uis/web/src/lib/telemetry.ts): single `track(eventType, properties)`. Auto envelope. Queue; flush every 10s or at 20 events; `sendBeacon` on `visibilitychange` hidden; retry 3× exponential backoff; URL from `NEXT_PUBLIC_TELEMETRY_ENDPOINT` (fallback same default). Never `apiFetch`.
- `userId` is TinyDB `sub` / `profile.user_id` only — never email/password.
- Strip properties to the event allowlist.

## Instrumentation

| event_type | Where | Class |
| --- | --- | --- |
| `inbound_order_created` | delivery form success | mandatory |
| `outbound_order_created` | consumption form success | mandatory |
| `stock_threshold_triggered` | after outbound if remaining stock ≤ 24 | mandatory |
| `direct_stock_edit_rejected` | supplies list “Adjust stock” (no stock PATCH exists) | mandatory |
| `supply_expiry_flagged` | outbound `expiry_waste` success | mandatory |
| `inbound_order_validation_failed` | client qty/clinic fail on delivery | identified |
| `outbound_order_rejected` | overstock / `InsufficientStockError` | identified |
| `user_login_failed` / `user_login_succeeded` | login page / `loginRequest` | identified |
| `session_expired` | AuthProvider 401 | identified |
| `page_viewed` | protected pathname | identified |
| `api_latency_recorded` | `apiFetch` duration | identified |
| `frontend_error_raised` | `window.onerror` / `unhandledrejection` / `error.tsx` | identified |
| `web_vital_recorded` | Navigation Timing `loadEventEnd` once | identified (extra) |

Inventory properties: `clinic_id`, `country` (`US`/`UK` from product), `product_id`, `product_category` mapped to `medication` \| `ppe` \| `consumable` \| `equipment`, `quantity`; `department` only on clinical outbound (`general_consultation`).

## Tests

- pytest stub: 200 `{received}`, envelope validation, no persistence, env present.
- Jest: queue/batch, allowlist strip, no PII keys, `track` does not send envelope fields from caller.

## Out of scope for this branch

Supabase, bulk insert, `GET /telemetry/report`, website public telemetry.
