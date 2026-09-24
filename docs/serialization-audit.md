# HealthCore API serialization audit

**Date:** 2026-09-23  
**App:** `services/api` FastAPI `0.141.1` (requirement `>=0.115`) / Pydantic `2.13.4` (requirement `>=2.9.0`)  
**Stores:** TinyDB users/profiles/suppliers; SQLModel inventory; in-memory incident analysis  
**HTTP consumer:** [`uis/web`](../uis/web) only (`authApi.ts`, `inventory.ts`, `suppliersApi.ts`, `IncidentAnalyzer.tsx`). Website and `scripts/` do not call this API.

## Exclusions

Framework routes are out of scope: `GET /docs`, `GET /redoc`, `GET /openapi.json`, `GET /docs/oauth2-redirect`.

Error-handler JSON (`422 {detail, errors}`, HTTP `400` insufficient-stock `detail` string) is preserved, not redesigned.

## Method

Phase 1 inventory used live `GET /openapi.json` via TestClient plus `include_router` in [`app/main.py`](../services/api/app/main.py) and one real JSON body per JSON route (seed/dev data; tokens and hashes not recorded). Original ✅ / ⚠️ / ❌ statuses below are the **pre-change** classifications and are not rewritten. Final status is **compliant** after Phase 3.

## Summary (original)

| Class | Count | Meaning |
|-------|------:|---------|
| ✅ | 21 | Explicit output contract; keep after consumer check |
| ⚠️ | 4 | Serialized but wrong shape, undocumented special response, or sensitive field |
| ❌ | 2 | Untyped JSON (`dict` / OpenAPI `object`) |
| **Application routes** | **27** | Six routers + `/health` |

⚠️: `POST /users` (email on public register), `DELETE /users/{user_id}` (204 undocumented), `GET /api/incidents/results/export` (CSV advertised as JSON), `GET /suppliers` (shared list/detail — **keep shared** after consumer check).  
❌: `GET /health`, `POST /api/incidents/analyze`.

---

## Auth

### `POST /auth/login`

| Column | Value |
|--------|--------|
| Purpose | Staff JWT login (`username` = email) |
| Auth | None |
| Consumer | `loginRequest` (`access_token` only) |
| Current | `response_model=TokenResponse`. Live keys: `access_token`, `token_type` |
| Original | ✅ |
| Risks | Token in body is the login product; must not add email/password/hash |
| Target | `TokenResponse`: `access_token`, `token_type` |
| Relationship | n/a |
| Input | `OAuth2PasswordRequestForm` (`username`, `password`) |
| Change | None |
| Validation | existing `test_login.py` + payload tests |
| Final | compliant |

### `GET /auth/me`

| Column | Value |
|--------|--------|
| Purpose | Current user for AuthGuard / profile |
| Auth | Bearer |
| Consumer | `fetchMe` (`email`, `role`, `profile.{id,user_id,name,phone,address}`) |
| Current | `response_model=MeResponse`. Live keys: `email`, `role`, `profile.id`, `profile.user_id`, `profile.name`, `profile.phone`, `profile.address` |
| Original | ✅ |
| Risks | Email is required by the profile consumer; do not drop |
| Target | `MeResponse`: `email`, `role`, `profile` (`ProfilePublic`: `id`, `user_id`, `name`, `phone`, `address`) |
| Relationship | Nested `profile` (already) |
| Input | none |
| Change | None |
| Validation | `test_me.py` + payload tests |
| Final | compliant |

### `POST /auth/forgot-password`

| Column | Value |
|--------|--------|
| Purpose | Trigger reset email without enumerating accounts |
| Auth | None |
| Consumer | `forgotPassword` (`detail` string) |
| Current | `response_model=MessageResponse`. Live keys: `detail` |
| Original | ✅ |
| Risks | Must not echo email, tokens, or hashes |
| Target | `MessageResponse`: `detail` |
| Relationship | n/a |
| Input | `ForgotPasswordRequest`: `email` |
| Change | None |
| Validation | `test_forgot_password.py` + payload tests |
| Final | compliant |

### `POST /auth/reset-password`

| Column | Value |
|--------|--------|
| Purpose | Consume one-time reset JWT |
| Auth | None |
| Consumer | `resetPassword` (ignores body on success) |
| Current | `response_model=MessageResponse`. Success keys: `detail` |
| Original | ✅ |
| Risks | Must not echo token, email, or password |
| Target | `MessageResponse`: `detail` |
| Relationship | n/a |
| Input | `ResetPasswordRequest`: `token`, `new_password` |
| Change | None |
| Validation | `test_reset_password.py` + payload tests |
| Final | compliant |

### `POST /auth/change-password`

| Column | Value |
|--------|--------|
| Purpose | Authenticated password change |
| Auth | Bearer |
| Consumer | `changePassword` (ignores body) |
| Current | `response_model=MessageResponse`. Live keys: `detail` |
| Original | ✅ |
| Risks | Must not echo passwords or hashes |
| Target | `MessageResponse`: `detail` |
| Relationship | n/a |
| Input | `ChangePasswordRequest`: `current_password`, `new_password` |
| Change | None |
| Validation | `test_change_password.py` + payload tests |
| Final | compliant |

---

## Users

### `POST /users`

| Column | Value |
|--------|--------|
| Purpose | Public registration (always role `user`) |
| Auth | None |
| Consumer | `registerRequest` — **ignores JSON body**, then logs in with the submitted email |
| Current | `response_model=UserPublic` **201**. Live keys: `id`, `email`, `is_active`, `role`, `created_at` |
| Original | ⚠️ unauthenticated response includes `email` (evaluator rule 9) |
| Risks | Email disclosure on a public endpoint |
| Target | `UserRegisteredResponse`: `id`, `role`, `is_active` (no email, no secrets) |
| Relationship | n/a (profile created server-side; not returned) |
| Input | `UserCreate`: `email`, `password`, `name?`, `phone?`, `address?` (not `UserPublic`; extra ignored) |
| Change | New register output schema; keep `UserCreate` |
| Validation | update `test_register.py`; payload tests |
| Final | compliant |

### `GET /users`

| Column | Value |
|--------|--------|
| Purpose | List users (tests/docs; no `uis/web` caller) |
| Auth | Bearer |
| Consumer | pytest / OpenAPI only |
| Current | `response_model=list[UserPublic]`. Item keys: `id`, `email`, `is_active`, `role`, `created_at` |
| Original | ✅ explicit, no hash |
| Risks | Authenticated email list is acceptable; never `hashed_password` |
| Target | `list[UserPublic]`: `id`, `email`, `is_active`, `role`, `created_at` |
| Relationship | n/a |
| Input | none |
| Change | None (keep email on authenticated list) |
| Validation | `test_users.py` + matrix |
| Final | compliant |

### `GET /users/{user_id}`

| Column | Value |
|--------|--------|
| Purpose | Self or admin user detail |
| Auth | Bearer (self or admin) |
| Consumer | pytest / OpenAPI only |
| Current | `response_model=UserPublic`. Live keys: `id`, `email`, `is_active`, `role`, `created_at` |
| Original | ✅ |
| Risks | No hash |
| Target | `UserPublic`: `id`, `email`, `is_active`, `role`, `created_at` |
| Relationship | n/a |
| Input | path `user_id` |
| Change | None |
| Validation | `test_users.py` |
| Final | compliant |

### `PUT /users/{user_id}`

| Column | Value |
|--------|--------|
| Purpose | Update credentials (email/password; admin role/`is_active`) |
| Auth | Bearer (self or admin) |
| Consumer | pytest / OpenAPI only |
| Current | `response_model=UserPublic`. Live keys: `id`, `email`, `is_active`, `role`, `created_at` |
| Original | ✅ write schema is `UserUpdate`, not `UserPublic` |
| Risks | Clients must not set `id`, `hashed_password`, `created_at` |
| Target | `UserPublic` (same fields) |
| Relationship | n/a |
| Input | `UserUpdate`: `email?`, `password?`, `role?`, `is_active?` |
| Change | Document extra-ignore of server-managed fields |
| Validation | `test_users.py` + write-schema tests |
| Final | compliant |

### `DELETE /users/{user_id}`

| Column | Value |
|--------|--------|
| Purpose | Delete user (self or admin) |
| Auth | Bearer |
| Consumer | pytest only |
| Current | `status_code=204`, return `None`. OpenAPI `schema=None` |
| Original | ⚠️ special non-JSON without an explicit contract |
| Risks | Must not return a JSON user dump |
| Target | `response_model=None`, `status_code=204`, documented `204` response |
| Relationship | n/a |
| Input | path `user_id` |
| Change | Explicit FastAPI 204 contract |
| Validation | `test_users.py` + OpenAPI 204 check |
| Final | compliant |

---

## Profiles

### `GET /profiles/me`

| Column | Value |
|--------|--------|
| Purpose | Own profile |
| Auth | Bearer |
| Consumer | profile page via `fetchMe` nested profile; this route is also used by tests |
| Current | `response_model=ProfilePublic`. Live keys: `id`, `user_id`, `name`, `phone`, `address` |
| Original | ✅ |
| Risks | No email/password |
| Target | `ProfilePublic`: `id`, `user_id`, `name`, `phone`, `address` |
| Relationship | Flat; `user_id` not nested user |
| Input | none |
| Change | None |
| Validation | `test_profiles.py` |
| Final | compliant |

### `PUT /profiles/me`

| Column | Value |
|--------|--------|
| Purpose | Update own name/phone/address |
| Auth | Bearer |
| Consumer | `updateMyProfile` |
| Current | `response_model=ProfilePublic`. Live keys: `id`, `user_id`, `name`, `phone`, `address` |
| Original | ✅ |
| Risks | Write schema must not accept `id` / `user_id` |
| Target | `ProfilePublic` (same fields) |
| Relationship | Flat |
| Input | `ProfileUpdate`: `name?`, `phone?`, `address?` |
| Change | None |
| Validation | `test_profiles.py` + write-schema tests |
| Final | compliant |

---

## Health and incidents

### `GET /health`

| Column | Value |
|--------|--------|
| Purpose | Liveness for Compose / CORS tests |
| Auth | None |
| Consumer | `docker compose` healthcheck, `test_cors.py`, `test_incidents_api.py` |
| Current | Decorator has **no** `response_model`; annotation `dict[str, str]`. OpenAPI `object`. Live keys: `status` |
| Original | ❌ not serialized |
| Risks | Untyped dump if the handler grows |
| Target | `HealthResponse`: `status` |
| Relationship | n/a |
| Input | none |
| Change | Pydantic model + decorator `response_model` |
| Validation | route matrix + health test |
| Final | compliant |

### `POST /api/incidents/analyze`

| Column | Value |
|--------|--------|
| Purpose | Upload CSV, return analysis metrics |
| Auth | Bearer |
| Consumer | `IncidentAnalyzer` / `IncidentAnalysisResult` (`source_file`, `total_records`, `valid_count`, `invalid_count`, `invalid_breakdown[]{rule,label,count}`, `category_counts`, `status_counts`, `country_counts`, `satisfaction.{scored_cases,closed_valid,average_score,histogram}`) |
| Current | Return annotation `dict`; OpenAPI `object`; body from `summary_to_json` |
| Original | ❌ not serialized |
| Risks | Accidental extra keys / PHI if summarize changes |
| Target | `IncidentAnalysisResponse` matching the TS type (keep `summary_to_json` behind the schema) |
| Relationship | Nested `invalid_breakdown` and `satisfaction` |
| Input | multipart `file` |
| Change | `app/incidents/schemas.py` + decorator `response_model` |
| Validation | `test_incidents_api.py` + matrix |
| Final | compliant |

### `GET /api/incidents/results/export`

| Column | Value |
|--------|--------|
| Purpose | Download latest metrics as CSV |
| Auth | Bearer |
| Consumer | `IncidentAnalyzer` export (`text/csv` blob) |
| Current | `Response` `media_type=text/csv`. OpenAPI listed `application/json` |
| Original | ⚠️ special non-JSON mis-documented as JSON |
| Risks | Fake JSON schema in `/docs` |
| Target | `response_class=Response`; `responses` map `200 text/csv`; no JSON `response_model` |
| Relationship | n/a |
| Input | none (uses in-memory latest) |
| Change | Document CSV contract on the decorator |
| Validation | export content-type test + OpenAPI content key |
| Final | compliant |

---

## Suppliers

Shared output `Supplier`: `id`, `name`, `country`, `categories`, `monthly_rate`, `currency`, `status`, `compliance_agreement`, `contract_renewal_date`, `contact_email`, `notes`, `updated_at`.

`SupplierDirectory` **list table** uses: `id`, `name`, `notes`, `country`, `categories`, `monthly_rate`, `currency`, `updated_at`, `compliance_agreement`, `status`.  
`contact_email` and `contract_renewal_date` are **create-form only** (not table columns). `GET /suppliers/{id}` has **no UI caller**. Create/rate/status responses are merged into the same `Supplier[]` state, so list vs detail is **not** split.

### `GET /suppliers`

| Column | Value |
|--------|--------|
| Purpose | Directory list |
| Auth | Bearer |
| Consumer | `fetchSuppliers` → `SupplierDirectory` |
| Current | `response_model=list[Supplier]`. Live item keys: full `Supplier` |
| Original | ⚠️ same schema as detail; **keep full row** (rendered fields plus create-echo fields) |
| Risks | Slimming would drop notes/compliance/`updated_at` the table shows |
| Target | `list[Supplier]` (all twelve fields) |
| Relationship | Flat; categories as `list[str]` |
| Input | optional query `country`, `category`, `status` |
| Change | None |
| Validation | `test_suppliers_api.py` + matrix |
| Final | compliant |

### `GET /suppliers/{supplier_id}`

| Column | Value |
|--------|--------|
| Purpose | Single supplier |
| Auth | Bearer |
| Consumer | tests/docs only |
| Current | `response_model=Supplier` |
| Original | ✅ |
| Target | `Supplier` (same twelve fields) |
| Relationship | Flat |
| Input | path id |
| Change | None |
| Validation | suppliers tests |
| Final | compliant |

### `POST /suppliers`

| Column | Value |
|--------|--------|
| Purpose | Register supplier |
| Auth | Bearer |
| Consumer | `createSupplier` (uses returned `Supplier`) |
| Current | `response_model=Supplier` **201** |
| Original | ✅ |
| Target | `Supplier` |
| Relationship | Flat |
| Input | `SupplierCreate` (writable directory fields; not `id`/`updated_at`) |
| Change | None besides write-schema tests |
| Validation | suppliers tests + write-schema |
| Final | compliant |

### `PATCH /suppliers/{supplier_id}`

| Column | Value |
|--------|--------|
| Purpose | Partial update |
| Auth | Bearer |
| Consumer | tests/docs (`uis/web` uses rate/status helpers) |
| Current | `response_model=Supplier`; input `SupplierUpdate` (`extra=forbid`) |
| Original | ✅ |
| Target | `Supplier` |
| Input | `SupplierUpdate` |
| Change | None |
| Validation | suppliers tests |
| Final | compliant |

### `PATCH /suppliers/{supplier_id}/rate`

| Column | Value |
|--------|--------|
| Purpose | Update monthly rate |
| Auth | Bearer |
| Consumer | `updateSupplierRate` |
| Current | `response_model=Supplier` |
| Original | ✅ |
| Target | `Supplier` |
| Input | `SupplierRateUpdate`: `monthly_rate` |
| Change | None |
| Validation | suppliers tests |
| Final | compliant |

### `PATCH /suppliers/{supplier_id}/status`

| Column | Value |
|--------|--------|
| Purpose | Activate / suspend |
| Auth | Bearer |
| Consumer | `updateSupplierStatus` |
| Current | `response_model=Supplier` |
| Original | ✅ |
| Target | `Supplier` |
| Input | `SupplierStatusUpdate`: `status` |
| Change | None |
| Validation | suppliers tests |
| Final | compliant |

---

## Inventory

`MedicalSupplyCreate` vs `MedicalSupplyPublic` already split; `current_stock` is response-only. List and detail use the same public row because `MedicalSuppliesList` and `getSupply` both need `id`, `name`, `sku`, `category`, `unit`, `country`, `current_stock`.

`OrderMovement.supply` is nested `SupplySummary` (`id`, `name`, `sku`, `category`, `unit`, `country`) — not a full catalogue row. `MovementHistory` needs `supply.name` and `supply.unit`.

### `GET /inventory/products`

| Column | Value |
|--------|--------|
| Purpose | Catalogue with computed stock |
| Auth | Bearer |
| Consumer | `listSupplies` → `MedicalSuppliesList`, delivery/consumption selects |
| Current | `response_model=list[MedicalSupplyPublic]` |
| Original | ✅ |
| Target | `list[MedicalSupplyPublic]`: `id`, `name`, `sku`, `category`, `unit`, `country`, `current_stock` |
| Relationship | Flat |
| Input | none |
| Change | None |
| Validation | `test_inventory_products.py` |
| Final | compliant |

### `POST /inventory/products`

| Column | Value |
|--------|--------|
| Purpose | Create catalogue row (stock starts at 0) |
| Auth | Bearer |
| Consumer | tests/docs (UI does not create products) |
| Current | `response_model=MedicalSupplyPublic` **201** |
| Original | ✅ |
| Target | `MedicalSupplyPublic` (same seven fields) |
| Relationship | Flat |
| Input | `MedicalSupplyCreate`: `name`, `sku`, `category`, `unit`, `country` (`extra=ignore`) |
| Change | None |
| Validation | existing `test_client_cannot_set_current_stock` + write-schema |
| Final | compliant |

### `GET /inventory/products/{supply_id}`

| Column | Value |
|--------|--------|
| Purpose | Single supply (live stock for consumption form) |
| Auth | Bearer |
| Consumer | `getSupply` → `SupplyConsumptionForm` (`current_stock`) |
| Current | `response_model=MedicalSupplyPublic` |
| Original | ✅ |
| Target | `MedicalSupplyPublic` |
| Relationship | Flat |
| Input | path id |
| Change | None |
| Validation | inventory product tests |
| Final | compliant |

### `POST /inventory/orders/inbound`

| Column | Value |
|--------|--------|
| Purpose | Record delivery |
| Auth | Bearer |
| Consumer | `createDelivery` (ignores body; uses 201) |
| Current | `response_model=DeliveryPublic` **201**. SQLModel row via `from_attributes` |
| Original | ✅ |
| Target | `DeliveryPublic`: `id`, `supply_id`, `quantity`, `vendor_name`, `clinic_id`, `created_at`, `user_uuid` |
| Relationship | ids only (not nested supply) |
| Input | `DeliveryCreate`: `supply_id`, `quantity`, `vendor_name`, `clinic_id` |
| Change | Set `from_attributes=True` on the public model |
| Validation | `test_inventory_orders.py` (already rejects client `user_uuid`) |
| Final | compliant |

### `POST /inventory/orders/outbound`

| Column | Value |
|--------|--------|
| Purpose | Record consumption; 400 if insufficient stock |
| Auth | Bearer |
| Consumer | `createConsumption` |
| Current | `response_model=ConsumptionPublic` **201** |
| Original | ✅ |
| Target | `ConsumptionPublic`: `id`, `supply_id`, `quantity`, `consumption_type`, `clinic_id`, `created_at`, `user_uuid` |
| Relationship | ids only |
| Input | `ConsumptionCreate`: `supply_id`, `quantity`, `consumption_type`, `clinic_id` |
| Change | `from_attributes=True` on the public model |
| Validation | inventory order tests; keep 400 `detail` prefix |
| Final | compliant |

### `GET /inventory/orders`

| Column | Value |
|--------|--------|
| Purpose | Combined movement history |
| Auth | Bearer |
| Consumer | `listMovements` → `MovementHistory` (`supply.name`, `supply.unit`, `quantity`, `kind`/`consumption_type`, `created_at`, `user_uuid`) |
| Current | `response_model=list[OrderMovement]` |
| Original | ✅ nested `SupplySummary`, not full `MedicalSupplyPublic` |
| Target | `list[OrderMovement]`: `kind`, `id`, `supply_id`, `quantity`, `clinic_id`, `created_at`, `user_uuid`, `vendor_name?`, `consumption_type?`, `supply` (`SupplySummary`) |
| Relationship | Nested flat summary |
| Input | none |
| Change | None |
| Validation | inventory order tests |
| Final | compliant |

---

## `/docs` smoke (Phase 3)

Recorded from live OpenAPI + `GET /docs` (TestClient; no credentials or tokens):

| Check | Route | Result |
|-------|--------|--------|
| Auth | `POST /auth/login` | `200 application/json` → `#/components/schemas/TokenResponse` (`access_token`, `token_type`) |
| Slim/list | `POST /users` | `201 application/json` → `UserRegisteredResponse` required `id`, `role`, `is_active` (no email property) |
| Detail / relationship | `GET /inventory/orders` | array of `OrderMovement`; `supply` → `SupplySummary` |
| Extra | `GET /docs` | HTTP 200 |
| Extra | `GET /health` | `HealthResponse` |
| Extra | `DELETE /users/{user_id}` | documented `204` “User deleted”, no JSON content |
| Extra | `GET /api/incidents/results/export` | `200 text/csv` only |

---

## Phase 3 close-out

All 27 application rows are **compliant**. Original ✅ / ⚠️ / ❌ classifications above are unchanged.

Validation: `uv run pytest` from `services/api` — **104 passed**. New file `tests/test_serialization_audit.py` (route matrix, OpenAPI special contracts, auth payload secrets, write-schema isolation, incident schema). `uis/web` types unchanged — no Jest/typecheck run.
