# Inventory API (HCR-0188)

## Purpose

Authenticated medical-supply catalogue and movement API so clinics record deliveries and consumption without storing a mutable stock column.

## Final Behavior

- Six JWT routes under `/inventory`: list/create/get products; inbound/outbound orders; combined order history.
- `current_stock` = sum(deliveries) − sum(consumptions), computed on read. Supplies with no movements report 0.
- Over-consumption returns HTTP 400 with `Insufficient stock for supply '{name}'. Available: {available}, requested: {quantity}.` and does not write.
- Invalid `consumption_type` is 422. Clinic IDs 1–12. Country `US` or `UK`.
- Seed: 6 supplies, 4 deliveries, 3 consumptions; `HCR-PPE-001` stock 105.

## Architecture and Data Flow

FastAPI `services/api` → `app/routers/inventory.py` → `app/inventory/service.py` → SQLModel session (`app/database.py`). Users remain in TinyDB; movements store `user_uuid = str(user id)` from `get_current_user`. Postgres outbound locks the supply row (`SELECT … FOR UPDATE`); SQLite tests skip the lock.

## Important Files

- `services/api/app/routers/inventory.py`
- `services/api/app/inventory/models.py`
- `services/api/app/inventory/schemas.py`
- `services/api/app/inventory/service.py`
- `services/api/app/inventory/seed.py`
- `services/api/app/inventory/schema.sql`
- `services/api/app/database.py`
- `services/api/tests/test_inventory_*.py`

## Interfaces and Contracts

| Method | Path | Auth |
|--------|------|------|
| GET/POST | `/inventory/products` | Bearer |
| GET | `/inventory/products/{id}` | Bearer |
| POST | `/inventory/orders/inbound` | Bearer |
| POST | `/inventory/orders/outbound` | Bearer |
| GET | `/inventory/orders` | Bearer |

`DATABASE_URL` in `services/api/.env` (gitignored). Use `postgresql+psycopg://` and session pooler port 5432. Tests force a temp SQLite file.

## Decisions and Constraints

- No User/Profile tables in Postgres.
- Do not persist or accept `current_stock`.
- Do not invent product update/delete. Staff UI lives in `uis/web` (see [inventory-backoffice-ui.md](inventory-backoffice-ui.md)).
- Combined history uses `OrderMovement.kind` (`inbound` | `outbound`).

## Validation

Observed 2026-09-18: 16 inventory pytest passed; 96 full pytest; compileall ok; live seed 6/4/3 gloves 105; live HTTP/`/docs` smoke of evaluator-critical flows. Commands in [`TESTING.md`](../../TESTING.md).

## Maintenance Notes

Re-run `cd services/api && uv run pytest tests/test_inventory_products.py tests/test_inventory_orders.py tests/test_inventory_seed.py` after inventory changes. Hosted schema is `schema.sql` if tables are missing. Concurrent negative-stock protection is Postgres-only (`FOR UPDATE`).
