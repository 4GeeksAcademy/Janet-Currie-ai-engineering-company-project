# Implementation plan — Inventory backoffice UI (Milestone 5 Part 2)

Work lives in `uis/web` (App Router, port 3001), not `uis/backoffice`. Consume Part 1 `/inventory` only. Do not change the inventory backend unless a live contract bug is proven.

## Approach

- Protected chrome already wraps `AuthProvider` → `AuthGuard` → `BackofficeShell`. JWT is `localStorage` key `healthcore_access_token`.
- API origin is `NEXT_PUBLIC_API_BASE_URL` via `apiBaseUrl()` (default `http://localhost:8000`). Do not add `NEXT_PUBLIC_INVENTORY_API_URL`.
- All HTTP through `apiFetch`. Dedicated module `uis/web/src/lib/inventory.ts`.
- User-facing copy uses `toUserMessage`, except outbound HTTP `400` insufficient-stock `detail` shown inline.
- Four routes under `/backoffice/inventory/{products,orders/inbound,orders/outbound,orders}`.
- No catalogue create/edit/delete UI. No history edit/delete.

## Todos (completed)

1. `inventory.ts` types/API helpers, `InsufficientStockError`, `stockStatus`; `apiFetch` caller-abort vs timeout.
2. Four protected pages, inventory components, nav link, `supply_id` query preselect.
3. Jest for inventory module + evaluator-critical UI; typecheck, lint, build.
4. Browser smoke of four routes against the running API.
5. Memory-bank updates; phase guide archived after completion.
