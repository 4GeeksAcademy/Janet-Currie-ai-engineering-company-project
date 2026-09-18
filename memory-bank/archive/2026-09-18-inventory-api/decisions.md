# Decisions — Milestone 5 inventory API (archived)

| Decision | Rationale |
|----------|-----------|
| Inventory on existing `services/api`, not a new service | Course: extend checkout; evaluator hits `/inventory` |
| SQLModel + `postgresql+psycopg://`; users stay TinyDB | HCR-0188; no User/Profile in Postgres |
| `user_uuid = str(TinyDB doc id)` from JWT, never from the body | TinyDB has no UUID column |
| Router at `app/routers/inventory.py` (not `services/routers/`) | Matches existing FastAPI layout |
| `GET /inventory/orders` returns `OrderMovement` with `kind` inbound/outbound | Stable combined history |
| Pytest uses temp SQLite; Postgres outbound uses `SELECT … FOR UPDATE` | Isolation without secrets; SQLite cannot row-lock |
| Seed via `uv run seed-inventory` | Same pattern as `seed-auth` |
