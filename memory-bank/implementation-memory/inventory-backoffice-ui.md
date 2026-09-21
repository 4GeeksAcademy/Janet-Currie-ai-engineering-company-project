# Inventory backoffice UI

## Purpose

Authenticated staff views in `uis/web` to inspect medical-supply stock and record deliveries and consumption against the Part 1 `/inventory` API.

## Final Behavior

- Four protected routes: `/backoffice/inventory/products`, `/orders/inbound`, `/orders/outbound`, `/orders`.
- Unauthenticated visits redirect to `/login` via existing `AuthGuard`.
- Supplies list shows live `current_stock` plus Out of stock / Low stock / In stock (presentation only: 0 / 1–24 / 25+).
- Delivery and consumption forms preselect `?supply_id=` when the id exists in `GET /inventory/products`.
- Consumption refreshes stock with `GET /inventory/products/{id}`, aborts stale requests, blocks qty above displayed stock, and shows outbound `400` insufficient-stock `detail` inline.
- History is read-only: Delivery / Clinical use / Expiry waste plus inbound/outbound, `en-GB` datetime, `user_uuid`.

## Architecture and Data Flow

Protected pages → inventory components → `uis/web/src/lib/inventory.ts` → `apiFetch` (JWT `healthcore_access_token`) → FastAPI `/inventory`. Official stock is never recomputed in the UI.

## Important Files

- `uis/web/src/lib/inventory.ts`
- `uis/web/src/lib/apiClient.ts`
- `uis/web/src/components/inventory/`
- `uis/web/src/app/(protected)/backoffice/inventory/`
- `uis/web/src/components/BackofficeShell.tsx`
- `uis/web/src/lib/__tests__/inventory.test.ts`
- `uis/web/src/components/inventory/__tests__/inventoryViews.test.tsx`

## Interfaces and Contracts

- Origin: `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`). No `NEXT_PUBLIC_INVENTORY_API_URL`.
- Create bodies: `{ supply_id, quantity, vendor_name, clinic_id }` and `{ supply_id, quantity, consumption_type, clinic_id }`. Omit `user_uuid`, `current_stock`, `id`, `created_at`.
- Insufficient-stock `400` `detail` is shown as authored; other errors use `toUserMessage`.

## Decisions and Constraints

- UI lives in `uis/web`, not `uis/backoffice`.
- No catalogue create/edit/delete UI; `POST /inventory/products` unused.
- No history edit/delete, search, or pagination.
- Do not change the inventory backend unless a live contract bug is proven.

## Validation

Observed 2026-09-18: `npm test -w uis/web` 34 passed; lint clean; `next build` succeeded; typecheck passed; live smoke of auth redirect, stock 105, delivery, overstock warning, inline 400, and history of both kinds. Shipped in `afb1bed`.

## Maintenance Notes

Keep caller abort distinct from timeout so consumption stock refresh can ignore stale GETs. After a 400, keep the API message while stock refreshes. Re-run `npm test -w uis/web` and `npm run typecheck -w uis/web` after inventory UI changes.
