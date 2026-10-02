# HealthCore telemetry plan

## 1. Scope and business context

HealthCore operates 12 US/UK outpatient clinics. Telemetry covers staff backoffice (`uis/web`) usage: inventory inbound/outbound, auth, navigation, errors, and API latency. It never includes patient identifiers, diagnoses, emails, names, or passwords. `userId` is an opaque TinyDB id. `department` is a service type only.

## 2. Inventory-flow instrumentation points

1. Authenticated entry to `/backoffice/inventory/products` (`page_viewed`).
2. Client validation failure on inbound quantity/clinic (`inbound_order_validation_failed`).
3. Successful inbound submit (`inbound_order_created`).
4. Outbound blocked by stock (`outbound_order_rejected`).
5. Successful outbound (`outbound_order_created`).
6. Remaining stock ≤ 24 after outbound (`stock_threshold_triggered`).
7. Attempt to edit stock outside an order (`direct_stock_edit_rejected`).
8. Expiry waste outbound (`supply_expiry_flagged`).

## 3–5. Event catalogue

Every row completes: we capture `[event_type]` because we need to know `[hypothesis]`, which allows `[decision]`.

| event_type | Class | Category | Hypothesis | Decision |
| --- | --- | --- | --- | --- |
| `inbound_order_created` | mandatory | inventory | what is received, where, from whom | consolidate purchasing |
| `outbound_order_created` | mandatory | inventory | consumption rate by clinic/department | replenishment |
| `stock_threshold_triggered` | mandatory | inventory | how often clinics run short | escalate restock |
| `direct_stock_edit_rejected` | mandatory | inventory | whether staff bypass order controls | training |
| `supply_expiry_flagged` | mandatory | inventory | waste/compliance risk | use or dispose |
| `inbound_order_validation_failed` | identified | inventory | which products fail quantity/clinic checks | form UX |
| `outbound_order_rejected` | identified | inventory | insufficient-stock attempts | training / min stock |
| `user_login_failed` | identified | auth | failed login volume and reason class | lockout / support |
| `user_login_succeeded` | identified | auth | successful session starts | denominator for failure rate |
| `session_expired` | identified | auth | expired JWT during use | token TTL |
| `page_viewed` | identified | navigation | which sections operators visit | IA / training |
| `api_latency_recorded` | identified | performance | slow API calls | capacity |
| `frontend_error_raised` | identified | errors | uncaught UI failures | bug triage |
| `web_vital_recorded` | identified | performance | page load time | frontend budget |

## 6. Envelope

`eventId` (UUID), `timestamp` (ISO 8601), `sessionId`, `userId` (opaque or `anonymous`), `event_type`, `schemaVersion` (`1.0.0`), `requestId`, `properties` (allowlist only).

## 7–8. Allowlists and sensitivity

See [`event-schemas.json`](event-schemas.json). No event includes email, name, password, or PHI. Auth failure `reason` is `invalid_credentials` \| `session_expired` \| `network_error` only.

Inventory required properties: `clinic_id`, `country` (`US`/`UK`), `product_id`, `product_category` (`medication` \| `ppe` \| `consumable` \| `equipment`), `quantity`. `department` only on clinical outbound (`general_consultation`). App categories map: `ppe`→`ppe`, `medications`→`medication`, `consumables`/`wound_care`/`diagnostics`→`consumable`.

Stock threshold uses remaining `quantity` after outbound and the staff low band (≤24).

## 9. Stream vs batch

All capture events are **batch** (10s or 20 events) because operational decisions here are not second-level paging. `stock_threshold_triggered` is still batched; future alerting can switch to stream without changing `track()`.

## 10. Throttle / debounce

- `page_viewed`: one event per pathname change.
- `api_latency_recorded`: one per `apiFetch` completion (queue absorbs bursts).
- `web_vital_recorded`: once per page load.
- `frontend_error_raised`: message truncated to 200 chars; no stacks.

## 11. Risks and exclusions

**Discarded:** enquiry-form telemetry (public site, not backoffice); incident CSV contents; supplier notes text; raw JWT; emails.

**Privacy:** no patient data; no password/email in properties.

**Cost:** no per-keystroke or hover events.

Delivery for this capture phase: in-memory queue → stub `POST /telemetry/events` (no persist).
