# Spec — Milestone 5 inventory API (archived)

## Acceptance (met)

- Six authenticated `/inventory` routes on existing FastAPI.
- Domain names `MedicalSupply`, `SupplyDelivery`, `SupplyConsumption`.
- SQLModel/Postgres persistence; TinyDB users only.
- Computed `current_stock`; over-consumption `400` with exact message and no write.
- Seed 6/4/3 with `HCR-PPE-001` stock 105.
- Pytest on temp SQLite (16 inventory tests; 96 full suite).
- Live seed and `/docs` smoke 2026-09-18.

Course contract: [`Back-End-Inventory-Management-Context.md`](Back-End-Inventory-Management-Context.md).
