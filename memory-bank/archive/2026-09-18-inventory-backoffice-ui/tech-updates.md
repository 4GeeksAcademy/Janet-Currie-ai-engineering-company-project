# Tech updates — Inventory backoffice UI

## `uis/web`

- `src/lib/inventory.ts` — types, `stockStatus` / `stockStatusLabel`, `InsufficientStockError`, list/get/create/listMovements
- `src/lib/apiClient.ts` — `isAbortError`; caller-aborted `signal` rethrows; timeout abort still `ApiTimeoutError`
- `src/components/inventory/` — `MedicalSuppliesList`, `SupplyDeliveryForm`, `SupplyConsumptionForm`, `MovementHistory`, `SupplySelect`, `StockBadge`
- Protected pages under `src/app/(protected)/backoffice/inventory/`
- Nav: Inventory → `/backoffice/inventory/products` in `BackofficeShell.tsx`
- Jest: `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`; `jest.setup.ts`; coverage includes `inventory.ts`

## Env

- Reuse `NEXT_PUBLIC_API_BASE_URL` (`.env.example` / gitignored `.env.local`)
- Do not commit `.env.local`

## Docs

- Phase guide moved from repo root into this archive
- Durable notes: `memory-bank/implementation-memory/inventory-backoffice-ui.md`
