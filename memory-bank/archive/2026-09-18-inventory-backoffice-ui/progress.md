# Progress — Active iteration

## Current state

Milestone 5 Part 2 inventory backoffice UI is implemented in `uis/web`. Phase guide remains at root [`Backoffice-Inventory-Interface-Context.md`](../Backoffice-Inventory-Interface-Context.md) until the iteration is archived.

## Completed (this iteration)

- `uis/web/src/lib/inventory.ts`: types, `stockStatus`, `InsufficientStockError`, list/get/create/listMovements.
- `apiFetch` rethrows caller abort; timeout abort still maps to `ApiTimeoutError`.
- Four protected pages + inventory components + Inventory nav link + `?supply_id=` preselect.
- Jest: `inventory.test.ts`, `inventoryViews.test.tsx`, abort cases in `apiClient.test.ts`.
- Local `uis/web/.env.local` copied from `.env.example` (gitignored; `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`).

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API (HCR-0188).

## Validation results

HCR-0188 (2026-09-18): 16 inventory pytest passed; 96 full pytest; compileall ok; live seed 6/4/3 gloves 105; live `/docs` + HTTP smoke of evaluator-critical flows. Details in [`TESTING.md`](../TESTING.md).

Part 2 (2026-09-18):

- `npm test -w uis/web`: 34 passed, 3 suites (coverage on `apiClient.ts` + `inventory.ts`).
- `npm run lint -w uis/web`: no ESLint warnings or errors.
- `npm run build -w uis/web`: success; routes include the four `/backoffice/inventory/...` pages.
- `npm run typecheck -w uis/web`: passed after abort-mock `RequestInit` typing fix (an earlier run failed only because a concurrent `next build` had wiped `.next/types`).
- Live smoke (API `:8000`, web `:3001`): unauthenticated `/backoffice/inventory/products` → `/login`; registered staff user; supplies list showed live stock (gloves **105 box / In stock**, wound care humanized); delivery of 2 succeeded and stock became **107**; consumption loaded **107**, overstock warning blocked qty 200; stale-stock submit of 107 after a concurrent outbound 1 returned inline `Insufficient stock for supply 'Nitrile gloves (box of 100)'. Available: 106, requested: 107.` and refreshed stock; successful consumption of 1; history showed Delivery (inbound), Clinical use (outbound), Expiry waste (outbound), `en-GB` dates, `user_uuid`, no edit/delete.

## Blockers

- None for Part 2. Supabase MCP SQL still fails password auth; live checks used SQLAlchemy via `.env`.

## Unverified / observed

- Pre-existing AuthGuard hydration overlay (`src/components/AuthProvider.tsx`) appears on hard navigations in Next 15.2.4; dismissed with Escape and did not block the inventory flows. Not fixed in this iteration.

## Next steps

1. Archived 2026-09-18 under `memory-bank/archive/2026-09-18-inventory-backoffice-ui/`. Phase guide moved from repo root.

## Run commands (durable)

```bash
cd services/api
uv sync --group dev
uv run pytest
uv run seed-auth
uv run seed-inventory
uv run uvicorn app.main:app --reload --port 8000

npm test -w uis/web
npm run typecheck -w uis/web
npm run lint -w uis/web
npm run build -w uis/web
npm run dev -w uis/web
```

Last updated: 2026-09-18
