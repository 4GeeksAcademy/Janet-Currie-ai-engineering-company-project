# Context — Milestone 5 inventory API (archived)

## Goal

HCR-0188 authenticated inventory API on existing FastAPI `services/api`. Phase guide: [`Back-End-Inventory-Management-Context.md`](Back-End-Inventory-Management-Context.md).

## Scope

- Six `/inventory` routes; SQLModel tables `MedicalSupply`, `SupplyDelivery`, `SupplyConsumption`.
- Users stay TinyDB. `current_stock` computed. No inventory UI.

## Constraints

- No User/Profile tables in Postgres/Supabase.
- APIs only under `services/`.
- `user_uuid` is `str(TinyDB id)`.

## Relevant files

| Path | Role |
|------|------|
| `services/api/app/routers/inventory.py` | `/inventory` router |
| `services/api/app/inventory/` | models, schemas, service, seed, schema.sql |
| `services/api/app/database.py` | SQLModel engine/session |
