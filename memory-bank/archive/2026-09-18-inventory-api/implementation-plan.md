# Implementation plan — Inventory API (archived)

Completed 2026-09-18. Phase guide: [`Back-End-Inventory-Management-Context.md`](Back-End-Inventory-Management-Context.md).

## Delivered

- Six JWT-protected `/inventory` routes on `services/api`
- SQLModel tables; computed stock; over-consumption 400 with no write
- `uv run seed-inventory` (6/4/3; gloves 105)
- Pytest on temp SQLite; live Postgres seed and `/docs` smoke

## Out of scope (intentional)

- Inventory UI
- Product update/delete and direct stock adjustment
- Clinic/vendor/user relational tables
- Lot, expiry, reorder, PHI
