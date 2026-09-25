# HealthCore API

FastAPI surface for:

- Phase 2 incident CSV analysis (reuses `scripts/` validation)
- Milestone 09 supplier directory backed by **TinyDB** + **Pydantic**
- AUTH-01/03 staff authentication (TinyDB users/profiles, JWT bearer, Resend password reset)
- Milestone 5 inventory (SQLModel / Postgres; `current_stock` is computed)

`uis/web` (http://localhost:3001) is the authenticated client. `uis/website` (http://localhost:3000) stays public and does not call this API.

## Environment

```bash
cd services/api
cp .env.example .env
```

Set a real `SECRET_KEY` in `.env`. Never commit `.env` or API keys.

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | JWT signing secret (required) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime (default `60`) |
| `RESET_TOKEN_EXPIRE_MINUTES` | Password-reset token lifetime (default `30`) |
| `FRONTEND_BASE_URL` | Used to build reset links (`http://localhost:3001`) |
| `RESEND_API_KEY` | Resend API key; if empty, forgot-password still returns 200 and skips sending |
| `RESEND_FROM_EMAIL` | Resend `from` address (must be allowed by your Resend account) |
| `AUTH_SEED_ADMIN_EMAIL` | Local admin email for `seed-auth` |
| `AUTH_SEED_ADMIN_PASSWORD` | Local admin password for `seed-auth` |
| `DATABASE_URL` | Inventory SQLModel engine. Use `postgresql+psycopg://...` for Supabase. If unset, local SQLite at `data/inventory.sqlite`. Tests force a temp SQLite file. |
| `CORS_ORIGINS` | Comma-separated browser origins (default `http://localhost:3001,http://127.0.0.1:3001`) |

`cryptography` is pinned to `>=42,<45` so `pip`/`uv` can use a prebuilt wheel. `cryptography` 45+ may try to compile from source and fail without OpenSSL/pkg-config.

Users and profiles live in `data/auth.json` (gitignored via `data/`). Supplier seed data is a separate TinyDB file. Inventory tables live in Postgres when `DATABASE_URL` is set; pytest never opens that database.

## Auth routes

| Method | Path | Auth | Description |
|--------|------|------|------------|
| `POST` | `/users` | Public | Register. Always creates `role=user`. Optional `name`, `phone`, `address` go on the linked profile. |
| `GET` | `/users` | Bearer | List users |
| `GET` | `/users/{id}` | Bearer | Get one user (self or admin) |
| `PUT` | `/users/{id}` | Bearer | Update credentials. Only an admin may change `role`. |
| `DELETE` | `/users/{id}` | Bearer | Delete user and linked profile |
| `GET` | `/profiles/me` | Bearer | Current user's profile |
| `PUT` | `/profiles/me` | Bearer | Update name / phone / address |
| `POST` | `/auth/login` | Public | OAuth2 password form: `username` is the email, plus `password`. Returns `{ access_token, token_type: "bearer" }`. |
| `GET` | `/auth/me` | Bearer | Current email, role, and profile |
| `POST` | `/auth/forgot-password` | Public | Always `200` (no email enumeration). Emails a reset link via Resend when the address exists. |
| `POST` | `/auth/reset-password` | Public | `{ token, new_password }`. Invalid / expired / used token → `400`. |
| `POST` | `/auth/change-password` | Bearer | `{ current_password, new_password }`. Wrong current password → `400`. |

Missing or invalid access tokens return `401`. Cross-user credential updates return `403`. Successful reset or change-password marks unused reset tokens used; existing access JWTs are not revoked.

In `/docs`, use **Authorize** after `POST /auth/login` (OAuth2 password flow).

### Seed a local admin

`POST /users` cannot create an admin.

```bash
cd services/api
uv sync
uv run seed-auth
```

Or without `uv`:

```bash
python3 -m app.auth.seed
```

Default credentials (override with env): `admin@healthcore.example` / `HealthCore!dev-admin`.

## Supplier directory

All supplier routes require a bearer token.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/suppliers` | Register a supplier (Pydantic-validated) |
| `GET` | `/suppliers` | List suppliers (`country`, `category`, `status` query filters) |
| `GET` | `/suppliers/{id}` | Get one supplier |
| `PATCH` | `/suppliers/{id}` | Partial update |
| `PATCH` | `/suppliers/{id}/rate` | Update monthly rate (sets `updated_at`) |
| `PATCH` | `/suppliers/{id}/status` | Activate or suspend (no deletes) |

### Seed TinyDB

```bash
cd services/api
uv sync
uv run seed
```

This loads the exact 15 suppliers from `app/suppliers/seed_data.py`.

## Inventory (HCR-0188)

All `/inventory` routes require a bearer token. Staff identities stay in TinyDB (`user_uuid` is `str(user id)`). Stock is deliveries minus consumptions and is never stored.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/inventory/products` | List medical supplies with computed `current_stock` |
| `POST` | `/inventory/products` | Register a catalogue item (no `current_stock` in the body) |
| `GET` | `/inventory/products/{id}` | One supply + stock; `404` if missing |
| `POST` | `/inventory/orders/inbound` | Record a `SupplyDelivery` |
| `POST` | `/inventory/orders/outbound` | Record a `SupplyConsumption`; over-stock is `400` and does not write |
| `GET` | `/inventory/orders` | Combined inbound/outbound history (`kind` + nested supply) |

Consumption types: `clinical_use`, `expiry_waste`. Clinic IDs: 1–12. Country: `US` or `UK`.

Hosted Postgres schema: [`app/inventory/schema.sql`](app/inventory/schema.sql) (run in the Supabase SQL Editor if MCP cannot migrate).

```bash
cd services/api
uv run seed-auth
uv run seed-inventory
```

Seeded `HCR-PPE-001` stock is **105** (deliveries 100+40, consumptions 25+10). `SELECT ... FOR UPDATE` is used on Postgres outbound writes; SQLite tests do not lock rows (race possible only under concurrent SQLite writers).

## Incident endpoints

Incident analyze/export require a bearer token. `GET /health` stays public.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/incidents/analyze` | Upload CSV; returns JSON summary |
| `GET` | `/api/incidents/results/export` | Download last analysis as metrics CSV |
| `GET` | `/health` | Liveness check |

## Run API

```bash
cd services/api
cp .env.example .env   # then set SECRET_KEY
uv sync
uv run seed
uv run seed-auth
uv run seed-inventory
uv run uvicorn app.main:app --reload --port 8000
```

Or with a venv:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m app.auth.seed
uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000 — Docs: http://localhost:8000/docs  
CORS allows the internal UI at http://localhost:3001.

## Test

```bash
cd services/api
uv run pytest
uv run pytest tests/test_inventory_products.py tests/test_inventory_orders.py tests/test_inventory_seed.py
```

Auth tests isolate TinyDB with a temp file and mock Resend. Inventory tests isolate SQLModel on a temp SQLite file. They do not send real email or touch Supabase.
