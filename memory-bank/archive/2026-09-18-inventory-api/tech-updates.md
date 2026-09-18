# Tech updates — Inventory API

## Python (`services/api`)

- Dependencies: `sqlmodel`, `psycopg[binary]`
- `app/database.py` — SQLModel engine from `DATABASE_URL` (`postgresql+psycopg://` for Supabase; sqlite fallback)
- `app/inventory/` — models, schemas, service, seed, `schema.sql`
- `app/routers/inventory.py` registered in `app/main.py`
- Script: `uv run seed-inventory`
- Tests: `test_inventory_products.py`, `test_inventory_orders.py`, `test_inventory_seed.py`; `tests/helpers.py` forces sqlite

## Docs

- `services/api/README.md` inventory section
- Root `TESTING.md` HCR-0188
- Phase guide moved from repo root into this archive
- `.env.example` documents `DATABASE_URL` (never commit `.env`)
