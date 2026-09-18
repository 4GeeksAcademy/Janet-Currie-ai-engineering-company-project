-- HealthCore inventory tables (Postgres / Supabase).
-- Safe to run in the SQL Editor if MCP migrations are unavailable.
-- Does not create users; staff identities stay in TinyDB.

CREATE TABLE IF NOT EXISTS medical_supply (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    sku TEXT NOT NULL,
    category TEXT NOT NULL,
    unit TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS supply_delivery (
    id SERIAL PRIMARY KEY,
    supply_id INTEGER NOT NULL REFERENCES medical_supply (id),
    quantity INTEGER NOT NULL,
    vendor_name TEXT NOT NULL,
    clinic_id INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    user_uuid TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS supply_consumption (
    id SERIAL PRIMARY KEY,
    supply_id INTEGER NOT NULL REFERENCES medical_supply (id),
    quantity INTEGER NOT NULL,
    consumption_type TEXT NOT NULL,
    clinic_id INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    user_uuid TEXT NOT NULL
);
