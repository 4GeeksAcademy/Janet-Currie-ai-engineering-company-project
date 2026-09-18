# Milestone 5 Context: Backend Inventory Management

## Purpose

This document is the implementation handoff for **Milestone 5 only** of the HealthCore company project: a backend inventory-management API for medical supplies. It defines the required domain model, API surface, business rules, seed data, validation targets, and scope boundaries.

The implementation agent must use this document to plan and implement the milestone in the existing company project. Before changing application code, inspect the actual repository, its active `memory-bank/` files, the existing FastAPI/TinyDB authentication implementation, database configuration, dependency-management conventions, and test patterns. Do not create a new repository or a separate application. Example paths below are assignment targets, but they must be reconciled with the checkout as it exists.


## Company and Business Context

HealthCore is an outpatient healthcare company with 12 clinics across the United States and the United Kingdom:

- 9 clinics in Texas, Florida, and Georgia;
- 3 clinics in London and Manchester.

Clinics consume medical supplies every day, including syringes, personal protective equipment, wound-care materials, rapid diagnostic tests, and medications. They also receive replenishment shipments from certified healthcare vendors. Each clinic currently tracks stock in a local spreadsheet, so the company has no centralized view of supply availability.

Accurate inventory is both an operational and compliance need. Stockouts can interrupt patient care, while expired supplies create clinical risk. This milestone provides the backend foundation for a future clinical-operations dashboard.

The governing ticket is **HCR-0188**. Its central rules are:

- supply entries represent vendor deliveries;
- supply exits represent clinical consumption or expiry waste recorded by clinic staff;
- stock is the net of entries minus exits;
- stock must never be modified directly;
- all inventory routes use the `/inventory` prefix;
- staff identities come from the existing TinyDB user store;
- inventory data is operational data, not protected health information, but every inventory route must still require authentication.

## Milestone Goal

Build an authenticated FastAPI inventory API backed by SQLModel and the project's configured Supabase/PostgreSQL database. The API must manage a medical-supply catalogue, record deliveries and consumption events, calculate current stock from those immutable movements, prevent negative stock, and expose a combined movement history.

## Fixed Architecture and Data Boundaries

- Use the existing FastAPI service and register an inventory router under `/inventory`.
- Store inventory entities in SQLModel/Supabase/PostgreSQL.
- Continue to store users in TinyDB. Do **not** add a SQLModel, Supabase, or PostgreSQL user table.
- `SupplyDelivery.user_uuid` and `SupplyConsumption.user_uuid` refer to the authenticated TinyDB user's identifier.
- Clinic records are outside this milestone. Store `clinic_id` as an integer, not a foreign key.
- US and UK supply records coexist in one medical-supply table. `country` identifies the applicable regulatory jurisdiction.
- `current_stock` is a computed response value and must not be a persisted model column or caller-editable field.
- Reuse the existing authentication dependency and conventions. All routes defined in this document require a valid authenticated user.
- Keep database work behind the project's existing session dependency and service/repository conventions if such layers already exist. Do not introduce an unrelated architecture rewrite.

## Required Domain Entities

Use the following entity names exactly in models, schemas, and API responses. The assignment's generic `Product`, `InboundOrder`, and `OutboundOrder` concepts are renamed for the HealthCore domain.

### `MedicalSupply`

Represents one catalogue item.

| Field | Type | Requirements |
| --- | --- | --- |
| `id` | `int` primary key | Auto-incremented. |
| `name` | `str` | Human-readable supply name, for example `Nitrile gloves (box of 100)`. |
| `sku` | `str` | Internal catalogue code, for example `HCR-PPE-001`. |
| `category` | `str` | HealthCore categories are `ppe`, `wound_care`, `diagnostics`, `medications`, and `consumables`. |
| `unit` | `str` | Unit of issue, such as `box`, `unit`, `pack`, or `vial`. |
| `country` | `str` | Regulatory jurisdiction; allowed values are `US` and `UK`. Must appear in both the persistence model and response schema. |
| `current_stock` | `int` | Computed only. Include in response schemas, never in the stored SQLModel table or create request. |

The source does not explicitly define SKU uniqueness, update/delete operations, or catalogue archival behavior. Do not invent those API features unless a newer assignment or existing project contract requires them.

### `SupplyDelivery`

Represents a vendor shipment received at a clinic. It maps to the generic `InboundOrder` concept.

| Field | Type | Requirements |
| --- | --- | --- |
| `id` | `int` primary key | Auto-incremented. |
| `supply_id` | `int` foreign key | References `MedicalSupply`. |
| `quantity` | `int` | Number of units received. |
| `vendor_name` | `str` | Vendor name, for example `MedLine Industries` or `Cardinal Health UK`. |
| `clinic_id` | `int` | Receiving clinic, restricted to IDs 1 through 12; not a foreign key. |
| `created_at` | `datetime` | Set automatically when the record is created. |
| `user_uuid` | `str` | TinyDB UUID of the clinic administrator who confirmed the delivery. |

### `SupplyConsumption`

Represents supplies removed from usable stock during patient care or because they expired. It maps to the generic `OutboundOrder` concept.

| Field | Type | Requirements |
| --- | --- | --- |
| `id` | `int` primary key | Auto-incremented. |
| `supply_id` | `int` foreign key | References `MedicalSupply`. |
| `quantity` | `int` | Number of units consumed or discarded. |
| `consumption_type` | `str` | Must be exactly `clinical_use` or `expiry_waste`; validate in the request schema. |
| `clinic_id` | `int` | Clinic where consumption occurred, restricted to IDs 1 through 12; not a foreign key. |
| `created_at` | `datetime` | Set automatically when the record is created. |
| `user_uuid` | `str` | TinyDB UUID of the clinical or administrative staff member who recorded the event. |

## Required API Router

The assignment names the router file `services/routers/inventory.py` and requires `APIRouter(prefix="/inventory")`. Register that router with the existing FastAPI application in `services/main.py` or the equivalent concrete application entry point found in the repository.

All six routes are authenticated.

| Method | Path | Required behavior |
| --- | --- | --- |
| `GET` | `/inventory/products` | Return all medical supplies, each including computed `current_stock`. |
| `POST` | `/inventory/products` | Register a new `MedicalSupply`; do not accept or store `current_stock`. |
| `GET` | `/inventory/products/{id}` | Return one medical supply, including computed `current_stock`; return the project's standard not-found response when absent. |
| `POST` | `/inventory/orders/inbound` | Record a `SupplyDelivery` for an existing supply and authenticated TinyDB user. |
| `POST` | `/inventory/orders/outbound` | Record a valid `SupplyConsumption` for an existing supply and authenticated TinyDB user, subject to the no-negative-stock rule. |
| `GET` | `/inventory/orders` | Return all delivery and consumption movements together with their associated supply data. |

Request and response schemas should be explicit and separate where that prevents server-managed fields from being accepted from clients. At minimum, clients must not control `id`, `created_at`, or computed `current_stock`. The implementation agent must reconcile whether `user_uuid` is omitted from request bodies and derived from the authenticated user, or accepted and verified against that user; it must never be trusted as an unauthenticated arbitrary identity.

The source does not prescribe the exact combined-order response shape or ordering. The implementation plan should define a stable, documented representation that distinguishes deliveries from consumptions, includes the related supply data, and follows existing API conventions without changing the required endpoint.

## Business Rules

### 1. Current stock is derived, never stored

For each medical supply:

```text
current_stock = SUM(SupplyDelivery.quantity) - SUM(SupplyConsumption.quantity)
```

No route may directly set, increment, decrement, or overwrite a persisted stock value. `GET /inventory/products` and `GET /inventory/products/{id}` must calculate the value from movement records at read time. A supply with no movements should report stock consistently as zero.

### 2. Consumption must not produce negative stock

Before creating a `SupplyConsumption`, calculate the selected supply's current stock. If the requested quantity exceeds the available amount, reject the request before any write occurs.

The response must be HTTP `400` with this exact message template:

```text
Insufficient stock for supply '{name}'. Available: {available}, requested: {quantity}.
```

The failed request must not create a partial consumption record or otherwise alter inventory.

### 3. Consumption type is constrained

`consumption_type` accepts only:

- `clinical_use` — used during patient care;
- `expiry_waste` — expired stock that was discarded.

An invalid value must fail request-schema validation and must not be written.

### 4. User references remain cross-store identifiers

Inventory movements store a string `user_uuid` referring to a user in TinyDB. This is an application-level cross-store relationship, not a SQL foreign key. Do not duplicate users in the relational database.

### 5. Country is required

Each `MedicalSupply` must have `country` set to `US` or `UK`. The field must exist in the SQLModel and every relevant request/response schema.

### 6. Clinic IDs are bounded values

Both movement entities require an integer `clinic_id` from 1 through 12. Clinic data is managed elsewhere, so no clinic table or relationship is part of this milestone.

### 7. Validate referenced supplies

Inbound and outbound movements must refer to an existing `MedicalSupply`. Handle an unknown `supply_id` through the project's normal client-safe not-found behavior, without creating a movement.

### 8. Movement quantities must be operationally valid

The source describes quantities as units received or consumed and evaluates insufficient stock. The implementation plan should explicitly confirm and enforce the project's normal positive-integer rule for movement quantities so zero or negative values cannot create meaningless deliveries or increase stock through a negative consumption. Treat this as a necessary validation inference unless newer course material specifies a different contract.

## Authentication and Authorization

- Every `/inventory` endpoint requires authentication, including catalogue reads.
- Reuse the existing TinyDB/JWT current-user mechanism from the prior authentication milestone.
- Missing, malformed, expired, or otherwise invalid credentials should follow the existing authentication API's `401` contract.
- Associate new movement records with the authenticated user's TinyDB UUID.
- Do not accept an arbitrary caller-supplied `user_uuid` without verifying it against the authenticated identity.
- No new role matrix is specified for this milestone. Do not invent broad role-based restrictions unless the existing application already imposes them or the instructor provides additional requirements.
- Inventory records must not include patient data. This API tracks operational supplies only and must not become a path for storing protected health information.

## Required Local Seed Data

Create the following records when setting up the local development database. Seed logic must follow existing project conventions and be safe to run in the intended setup workflow. It must not use production data or credentials.

### Medical supplies: minimum 6

| `name` | `sku` | `category` | `unit` | `country` |
| --- | --- | --- | --- | --- |
| Nitrile gloves (box of 100) | `HCR-PPE-001` | `ppe` | `box` | `US` |
| Surgical mask (pack of 50) | `HCR-PPE-002` | `ppe` | `pack` | `UK` |
| Adhesive wound dressing | `HCR-WND-001` | `wound_care` | `box` | `US` |
| Rapid strep test kit | `HCR-DIAG-001` | `diagnostics` | `unit` | `US` |
| Blood glucose test strips (50) | `HCR-DIAG-002` | `diagnostics` | `box` | `UK` |
| 0.9% Saline solution 500ml | `HCR-MED-001` | `medications` | `vial` | `US` |

### Supply deliveries: minimum 4

- Create at least four delivery records.
- Include at least two deliveries for `HCR-PPE-001`, using different quantities.
- Use realistic vendors such as `MedLine Industries`, `Cardinal Health UK`, and `Bound Tree Medical`.
- Mix clinic IDs across the US and UK clinic set.
- Use authenticated-user UUID values that exist in the local TinyDB instance.

### Supply consumptions: minimum 3

- Create at least three consumption records.
- Include at least one `clinical_use` event.
- Include at least one `expiry_waste` event.
- Seeded consumption must not exceed the deliveries available for the affected supply.
- Use user UUIDs that exist in the local TinyDB instance.

Seed values must make the net-stock calculation easy to verify, especially for `HCR-PPE-001` with its multiple deliveries.

## Assignment File Layout

The authoritative context provides this target structure inside `services/`:

```text
services/
├── main.py
├── database.py          # TinyDB client, SQLModel engine, and get_db dependency
├── models.py            # MedicalSupply, SupplyDelivery, SupplyConsumption
├── schemas.py           # Pydantic request and response schemas
└── routers/
    └── inventory.py     # APIRouter(prefix="/inventory")
```

Treat this as the expected course layout, not permission to overwrite or duplicate working repository modules. The implementation agent must map these responsibilities to the actual checkout and make the smallest compatible changes. If the repository already separates models, schemas, services, or database dependencies differently, preserve those conventions while retaining the required router location and public API contract wherever the evaluator depends on them.

## Implementation Planning Checklist

Before writing code, the implementation agent should identify:

- the FastAPI application entry point and router-registration pattern;
- the SQLModel engine, session dependency, migration/table-creation strategy, and Supabase/PostgreSQL configuration;
- the TinyDB user model and exact type/format of its user ID;
- the reusable authentication/current-user dependency;
- existing model, schema, service, error-response, and timestamp conventions;
- how relational tables are created or migrated in local and hosted environments;
- current test fixtures and database-isolation strategy;
- the appropriate location and idempotency behavior for seed data;
- the concrete combined movement-history response contract;
- all places where a caller might otherwise be able to set `current_stock`, timestamps, IDs, or another user's UUID.

The implementation plan should name the concrete files to change, schemas to add, query strategy for computed stock, atomicity approach for outbound validation/write, seed mechanism, tests, and validation commands.

## Concurrency and Data-Integrity Consideration

The required “check available stock, then write consumption” operation is vulnerable to concurrent requests if both observe the same balance before either commits. The source does not prescribe a locking mechanism, but the implementation agent must evaluate the database and transaction facilities already in use and choose the smallest practical approach that keeps the availability check and insert consistent. At minimum, document any remaining race risk; do not claim negative stock is impossible under concurrency unless it has been enforced and tested at the persistence boundary.

## Required Validation and Test Coverage

Use the repository's existing testing tools and patterns. Add focused tests for observable behavior and public contracts rather than framework internals. At minimum, verify:

- authenticated product creation succeeds with valid required fields;
- all product-list entries and the single-product response include correct computed `current_stock`;
- a supply with no movements reports zero stock;
- multiple deliveries add together and consumptions subtract from the total;
- `current_stock` is not stored or accepted from a client;
- a valid inbound movement is persisted with its supply, clinic, timestamp, and authenticated TinyDB user UUID;
- valid `clinical_use` and `expiry_waste` movements are accepted;
- an outbound movement equal to available stock succeeds and leaves zero;
- an outbound movement greater than available stock returns HTTP `400`, uses the exact required message, and performs no write;
- an invalid `consumption_type` returns a schema-validation error and performs no write;
- missing or unknown supply IDs are rejected without partial writes;
- `country` is present in the model and response and rejects values outside `US`/`UK` if schema constraints are implemented;
- clinic IDs outside 1–12 are rejected if the required bound is enforced in the schema;
- zero and negative movement quantities are rejected under the positive-quantity validation inference;
- all routes reject unauthenticated requests according to the existing auth contract;
- movement `user_uuid` cannot impersonate another TinyDB user;
- `GET /inventory/orders` returns both movement types with related supply data and a stable distinction between them;
- seed data satisfies the required counts, types, and nonnegative balances.

Run the narrowest inventory tests first, then the applicable full backend suite, lint/type checks, and a FastAPI smoke test against the configured local database. Manually exercise the evaluator-critical flows through `/docs` if that is part of the project's established validation. Record exact commands and observed results in the active memory bank; never claim a check passed unless it was actually run.

## Evaluator-Critical Checks

The implementation will be specifically evaluated for these behaviors:

1. Creating a `SupplyConsumption` that exceeds available stock returns HTTP `400` and does not write the event.
2. Creating a `SupplyConsumption` with a value other than `clinical_use` or `expiry_waste` produces a validation error.
3. `GET /inventory/products` reports `current_stock` as deliveries minus consumptions, including seeded movement data.
4. `country` exists in both the `MedicalSupply` model and its response schema.
5. `clinic_id` exists on both `SupplyDelivery` and `SupplyConsumption`.

These checks are mandatory, not optional examples.

## Acceptance Criteria

Milestone 5 is complete only when all of the following are true:

- The existing FastAPI app exposes the six required authenticated routes under `/inventory`.
- The exact domain entity names `MedicalSupply`, `SupplyDelivery`, and `SupplyConsumption` are used.
- Inventory entities persist through the project's SQLModel/Supabase/PostgreSQL setup.
- No SQLModel or Supabase user table is introduced; movement records reference TinyDB users through `user_uuid`.
- `MedicalSupply` includes `name`, `sku`, `category`, `unit`, and `country`, with computed `current_stock` returned by product reads.
- `current_stock` is never stored or directly modified.
- Deliveries increase computed stock and both consumption types decrease it.
- Over-consumption is rejected before writing with HTTP `400` and the exact required message.
- Invalid consumption types fail request validation.
- Both movement models include `clinic_id`; clinic IDs remain plain integers rather than foreign keys.
- All routes require valid authentication and new movements are tied safely to the authenticated TinyDB user.
- The local seed dataset contains at least 6 medical supplies, 4 deliveries, and 3 consumptions with the required examples and nonnegative balances.
- Product and order responses satisfy the documented schemas and do not leak internal or authentication data.
- Focused tests cover the evaluator-critical behavior, realistic validation failures, authentication, and no-partial-write guarantees.
- Applicable backend tests and checks pass with actual observed results.
- Existing behavior outside this inventory milestone remains unchanged.

## Scope Boundaries

In scope:

- medical-supply catalogue creation and reads;
- delivery and consumption recording;
- computed stock;
- negative-stock prevention;
- combined movement history;
- authentication integration;
- SQLModel/Supabase persistence;
- local seed data;
- focused tests and only the documentation/configuration necessary for this milestone.

Out of scope unless a newer requirement explicitly adds it:

- frontend or backoffice inventory screens;
- direct stock adjustment endpoints;
- product update or deletion endpoints;
- vendor, clinic, procurement, patient, billing, or user tables;
- patient-level consumption records or any PHI;
- lot/batch, serial-number, barcode, expiration-date, reorder-point, transfer, valuation, forecasting, or reporting features;
- role-system redesign;
- unrelated refactors, deployment changes, or infrastructure work.

## Handoff Expectations

The implementation agent should begin by inspecting the real repository and producing a repository-grounded plan. During work, keep the active `memory-bank/` files current with material decisions, progress, validation results, blockers, and next steps.

Before declaring completion:

1. Reconcile every required route, field, rule, and seed-data condition against this document.
2. Verify the five evaluator-critical checks with actual tests or observed API behavior.
3. Confirm the relational inventory/TinyDB user boundary was preserved.
4. Confirm no direct-stock mutation path or partial failed consumption write exists.
5. Record exact validation commands and results.
6. Create or update durable implementation memory only after the milestone has genuinely been finalized.
