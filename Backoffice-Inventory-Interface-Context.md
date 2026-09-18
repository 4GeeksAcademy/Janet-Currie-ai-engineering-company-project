# Milestone 5 Part 2 Context: Backoffice Inventory Management Interface

## Purpose

This document is the implementation handoff for **Part 2 of Milestone 5 only**: the authenticated HealthCore backoffice interface for inventory management. It translates the supplied backoffice assignment into the company-specific terminology and backend contract established in `context.md`.

The implementation agent must add this interface to the existing Next.js backoffice in the company monorepo. Do not create a new repository, a new frontend application, or a replacement inventory backend. Before planning or changing code, inspect the actual checkout, the active `memory-bank/` files, the completed inventory API, the existing authentication implementation, the backoffice route structure, shared components, styling system, API utilities, and test conventions. Use concrete paths and patterns found in the repository rather than assuming that illustrative filenames already exist.


## Authoritative Inputs

Use these inputs together:

1. The supplied **Milestone 5 — Backoffice: Inventory Management Interface** assignment.
2. The HealthCore backend inventory handoff in `context.md`.
3. The inventory API's live OpenAPI contract and actual response schemas after the backend implementation is complete.
4. Existing repository conventions and current instructor direction.

When the generic assignment uses `Product`, `InboundOrder`, and `OutboundOrder`, the HealthCore interface must use the company vocabulary defined in `context.md`:

| Generic concept | HealthCore term |
| --- | --- |
| Product | Medical supply (`MedicalSupply`) |
| Inbound order | Supply delivery (`SupplyDelivery`) |
| Outbound order | Supply consumption (`SupplyConsumption`) |
| Outbound reason/type | Consumption type |
| Inventory owner/creator | Authenticated staff member identified by TinyDB `user_uuid` |

The required URLs retain the assignment's `/products` and `/orders` segments even though visible labels should use HealthCore terminology.

## Business Context

HealthCore operates 12 outpatient clinics in the United States and United Kingdom. Clinic staff receive medical supplies from vendors, consume supplies during patient care, and discard expired stock. The backend API from Part 1 centralizes those movements and computes stock, but staff need an efficient backoffice interface to use it without Postman or another REST client.

This is an internal operations tool. Optimize for clarity, speed, accessibility, reliable feedback, and prevention of data-entry mistakes rather than marketing presentation. Staff must be able to see current stock, record deliveries, record clinical use or expiry waste, and review the movement history.

Inventory data is operational rather than patient data. Do not introduce patient information or protected health information into these views.

## Part 2 Goal

Add four authenticated, live-data inventory views to the existing Next.js backoffice:

1. a medical-supplies stock list;
2. a supply-delivery form;
3. a supply-consumption form with reactive stock availability;
4. a read-only combined movement-history page.

All API access must go through one dedicated inventory integration module. Every user-triggered operation must produce an understandable success or failure state, and no API error may be silently swallowed or exposed as raw JSON.

## Existing Backend Contract

Part 2 consumes the Part 1 API; it must not recreate its business logic in the browser.

| Method | Backend endpoint | Frontend use |
| --- | --- | --- |
| `GET` | `/inventory/products` | Load all medical supplies and their computed `current_stock`. |
| `GET` | `/inventory/products/{id}` | Refresh and display current stock for the selected medical supply. |
| `POST` | `/inventory/orders/inbound` | Record a vendor delivery. |
| `POST` | `/inventory/orders/outbound` | Record clinical consumption or expiry waste. |
| `GET` | `/inventory/orders` | Load the combined delivery/consumption history with supply data. |

The product-creation endpoint from Part 1 is not used by any required Part 2 view. Adding a create, update, or delete medical-supply interface is outside this assignment unless a newer requirement explicitly asks for it.

### `MedicalSupply` fields displayed by the UI

- `id`
- `name`
- `sku`
- `category`: `ppe`, `wound_care`, `diagnostics`, `medications`, or `consumables`
- `unit`: for example `box`, `unit`, `pack`, or `vial`
- `country`: `US` or `UK`
- `current_stock`: computed by the backend from deliveries minus consumptions

### Supply-delivery request fields

The delivery form must collect the client-editable fields required by the implemented API:

- `supply_id`, selected by medical-supply name rather than typed as a raw ID;
- `quantity`;
- `vendor_name`;
- `clinic_id`, an integer from 1 through 12.

The API should own `id`, `created_at`, and the authenticated staff member's `user_uuid`. If the final backend contract accepts `user_uuid`, the frontend must follow that documented contract without allowing the user to impersonate another account.

### Supply-consumption request fields

The consumption form must collect:

- `supply_id`, selected by medical-supply name rather than typed as a raw ID;
- `quantity`;
- `consumption_type`, restricted to `clinical_use` or `expiry_waste`;
- `clinic_id`, an integer from 1 through 12.

The API remains the source of truth for available stock, negative-stock prevention, timestamps, identity, and persistence.

### Movement-history fields

Every visible history row must include:

- medical-supply name;
- quantity;
- movement type, clearly identified as delivery/inbound or consumption/outbound;
- creation date;
- creator `user_uuid`.

The exact `GET /inventory/orders` response shape was not fixed by the Part 1 scenario. Inspect the implemented OpenAPI schema and payload before coding. If delivery and consumption records have different shapes, normalize them in the inventory integration layer into a stable UI-facing type rather than scattering response-shape checks across components. Preserve useful domain-specific details such as vendor name or consumption type when the response provides them, but the five required columns above are mandatory.

## Application Location and Configuration

- Work inside the existing `uis/backoffice` Next.js application.
- Use the repository's current package manager and lockfile. The assignment shows `npm install`, but do not replace an established workspace/package-manager convention.
- Read the inventory API origin from:

  ```text
  NEXT_PUBLIC_INVENTORY_API_URL=http://localhost:8000
  ```

- Keep the local value in `uis/backoffice/.env.local` or the configuration location already used by that app.
- Confirm `.env.local` is ignored and do not commit tokens or credentials.
- Do not hardcode the localhost origin in components or duplicate base-URL logic.
- Because `NEXT_PUBLIC_*` values are exposed to the browser, treat this value as configuration rather than a secret. Never put a server secret or privileged credential in it.
- The backend service must be running and reachable for live integration testing.

## Dedicated Inventory Integration Layer

Create or extend one client-side module, such as `uis/backoffice/lib/inventory.ts`, that owns every call to the inventory API. Follow a more specific existing API-client location if the repository already has one.

Components and route files must not call `fetch` directly for inventory operations.

The integration layer must:

- resolve and validate the configured API base URL;
- obtain the current access token through the existing backoffice authentication mechanism;
- attach `Authorization: Bearer <token>` to every inventory request;
- set appropriate request headers and serialize request bodies consistently;
- parse successful responses into explicit TypeScript types;
- normalize the order-history payload if inbound and outbound records differ;
- treat every non-2xx response as a failure;
- extract a readable FastAPI error from common response forms, especially `detail` as a string and validation `detail` arrays;
- provide a safe, human-readable fallback if the body is empty, malformed, or not JSON;
- preserve enough structured information, such as HTTP status, for the UI to distinguish validation errors, authentication failures, and unexpected server errors;
- never expose raw response objects, raw JSON blobs, stack traces, tokens, or internal details to users;
- integrate with the existing session-expiration behavior for `401` responses instead of inventing a second authentication system.

At minimum, expose typed operations equivalent to:

- list medical supplies;
- get one medical supply by ID;
- create a supply delivery;
- create a supply consumption;
- list and normalize inventory movements.

Names should follow repository conventions; the behavior matters more than these illustrative function names.

## Shared UI Behavior

Every inventory page must explicitly handle:

- initial loading;
- successful data or submission;
- empty data where applicable;
- recoverable API failure with a readable message and retry or other useful next action;
- expired, missing, or invalid authentication;
- pending form submission, with repeat submissions prevented;
- accessibility for keyboard and assistive-technology users.

Use existing backoffice layout, navigation, form controls, tables, alert components, and design tokens. Add an Inventory navigation entry if the backoffice's established information architecture requires one, but avoid unrelated navigation redesign.

Do not use color alone to communicate state. Stock levels and movement types must also have text, icons, labels, or other non-color cues. Confirmation and error messages should be visible, associated with the relevant operation, and announced appropriately by assistive technology using existing accessible components or live-region patterns.

## Required View 1: Medical Supplies

### Route

```text
/backoffice/inventory/products
```

### Data source

```text
GET /inventory/products
```

### Required behavior

- Load live medical-supply data through the inventory integration module.
- Display each supply's `name`, `sku`, `category`, `unit`, `country`, and `current_stock` unless the existing responsive table pattern requires a considered compact presentation.
- Present category and consumption terminology in readable HealthCore language while retaining the underlying API values.
- Make the numeric `current_stock` unambiguous and keep its unit visible or readily understandable.
- Apply an accessible visual stock indicator that distinguishes at least healthy stock from low stock.
- Define deterministic stock thresholds and document their rationale in a concise code comment near the stock-status function, as the assignment requires.
- Consider zero stock as a separately visible out-of-stock state when compatible with the chosen thresholds.
- Include clearly labelled actions on each row for recording a delivery and recording consumption for that supply.
- Prefer passing the selected supply through a stable query parameter or equivalent route state so the destination form can preselect it. The form must still validate the supplied ID against live product data and recover safely from missing or invalid values.
- Provide a clear empty state if no supplies exist.
- Provide a visible load-failure message and retry action if the request fails.

Stock color/status is a presentation aid only. It must not replace or reinterpret the backend's `current_stock` value.

## Required View 2: Register Supply Delivery

### Route

```text
/backoffice/inventory/orders/inbound
```

### Submission endpoint

```text
POST /inventory/orders/inbound
```

### Required behavior

- Load the available medical supplies and render a selector labelled with the HealthCore domain term.
- Show supply names in the selector; including SKU, country, or unit to disambiguate similar names is encouraged when supported by the existing UI pattern.
- Never require staff to type a raw `supply_id`.
- Accept the delivery quantity, vendor name, and clinic ID required by the backend contract.
- Constrain or validate `clinic_id` to the HealthCore range 1–12.
- Apply appropriate client-side required-field, type, and positive-quantity validation without treating it as a substitute for API validation.
- Disable or otherwise guard submission while product data is unavailable or a request is pending.
- Submit only through the inventory integration module.
- On success, clear/reset the form and show a visible confirmation message.
- On HTTP `400`, validation failure, server failure, network failure, or an unreadable response, show a readable visible error; do not rely on the console.
- Preserve the user's entries after a failed submission wherever doing so helps correction and retry.
- If the user arrived from a product-row action, preselect that valid supply.

Server-managed `id`, `created_at`, `current_stock`, and staff identity must not be editable inputs.

## Required View 3: Record Supply Consumption

### Route

```text
/backoffice/inventory/orders/outbound
```

### Submission endpoint

```text
POST /inventory/orders/outbound
```

### Required behavior

- Load medical supplies and render a name-based selector rather than a raw-ID field.
- Accept quantity, `consumption_type`, and clinic ID using clear HealthCore labels.
- Present exactly two consumption choices:
  - `clinical_use` — clinical use;
  - `expiry_waste` — expired supply discarded.
- Constrain or validate clinic ID to 1–12 and quantity to a positive whole number.
- If the user arrived from a product-row action, preselect that valid supply.

### Reactive current-stock requirement

When the selected supply changes:

1. Clear stock and quantity validation state associated with the previous selection.
2. Fetch the selected supply through `GET /inventory/products/{id}` using the integration module, even if the list response included stock, so the user sees a current value before submission.
3. Show a loading state while the selected supply is being refreshed.
4. Display the returned `current_stock` prominently with its supply unit.
5. If the stock lookup fails, display a readable error and prevent submission until a reliable value is available.
6. Prevent a slower response for an earlier selection from overwriting the state for a newer selection. Use the repository's existing request-cancellation or stale-response pattern.

Do not enable a quantity submission path until a product is selected and its current stock has loaded. This requirement is user guidance; the backend remains authoritative because stock can change between lookup and submission.

### Client-side overstock warning

- Compare the entered quantity with the displayed available stock.
- If quantity exceeds stock, show a clear warning before submission and associate it with the quantity field.
- Prevent an obviously invalid submission when doing so matches the existing form-validation pattern.
- Never remove backend handling on the assumption that the client check is sufficient.
- Treat a quantity equal to available stock as valid.

### Required HTTP 400 behavior

The backend may reject a request because another staff member consumed stock after the displayed balance was loaded. When `/inventory/orders/outbound` returns HTTP `400`:

- extract the API message, including the Part 1 insufficient-stock message when present;
- display it inline near the quantity/availability controls;
- keep the entered form values available for correction;
- refresh the selected supply's stock so the displayed balance reflects the backend's latest value;
- do not show raw JSON or fail silently.

On a successful submission, reset the form according to established UX conventions, show a confirmation message, and ensure any displayed stock is cleared or refreshed so stale availability is not presented as current.

## Required View 4: Inventory Movement History

### Route

```text
/backoffice/inventory/orders
```

### Data source

```text
GET /inventory/orders
```

### Required behavior

- Load live movement data through the inventory integration module.
- Render both deliveries and consumptions in one read-only history view.
- Each row must show medical-supply name, quantity, inbound/outbound type, creation date, and creator `user_uuid`.
- Distinguish supply deliveries from supply consumptions with an accessible label and visual treatment.
- Use clear HealthCore labels such as `Delivery`, `Clinical use`, and `Expiry waste` when the response contains enough information, while retaining a definite inbound/outbound distinction.
- Format dates consistently with the existing backoffice convention while preserving the underlying event time accurately.
- Provide a clear empty state and a visible error state with retry.
- Do not add edit or delete actions.

Sorting, searching, filtering, and pagination are not required by the supplied brief. Reuse existing table behavior if it is already automatic, but do not expand the milestone merely to add those features.

## Authentication and Route Protection

All four inventory pages and all five consumed endpoints require a valid login.

- Reuse the same authentication guard, provider, hook, layout, and token source already used by protected backoffice routes.
- The prior HealthCore authentication contract stores the JWT in the application's established client-side session flow; do not introduce a second token store.
- Redirect an unauthenticated user to the existing login page before rendering protected data.
- Avoid flashing protected inventory content while authentication status is still being resolved.
- Attach the current bearer token through the integration layer on every inventory request.
- Follow the existing expired/invalid-token behavior for `401`, normally clearing unusable session state and redirecting to login.
- Do not treat a `400` inventory rule failure or `403` permission failure as proof that the token is invalid.
- If the application supports returning to the originally requested page after login, preserve that established behavior.

Client-side route protection is a user-flow mechanism, not an authorization boundary. The backend must continue enforcing authentication.

## Error-Handling Contract

No operation may fail silently. No user-facing message may be only a console entry, raw JSON object, stack trace, or unexplained status code.

### Expected error presentation

- Product and history load errors: visible page-level message plus a retry action.
- Product-selector load errors: visible form-level message and disabled submission.
- Field validation: message associated with the relevant field.
- Outbound insufficient stock: API message inline near quantity/current stock.
- Other inbound/outbound API errors: visible form-level message that preserves correctable user input.
- Unexpected or malformed server response: safe fallback such as an inability to complete the operation, with a retry path.
- Network failure: distinguishable, readable feedback without promising that the server rejected the request if the outcome is unknown.
- Authentication failure: follow existing session-expiration and login-redirection behavior.

Success feedback is equally required for form submissions and must be visible rather than console-only.

## State and Data-Consistency Requirements

- The backend is the sole authority for persisted inventory and stock calculation.
- Never compute the official stock balance by mutating client state after a delivery or consumption.
- Re-fetch affected data after mutations where necessary to avoid stale stock/history.
- Do not use optimistic updates for supply consumption unless the project already has a safe reconciliation pattern; server rejection is a normal outcome when inventory changes concurrently.
- Prevent double submission while a mutation is pending.
- Discard or ignore stale product-stock responses after rapid selector changes.
- Keep server-provided identifiers and timestamps intact.
- Do not cache authenticated inventory data in a way that can leak it between users.

## Suggested File Responsibilities

The exact file structure must follow the real Next.js version and routing style found in `uis/backoffice`. A likely responsibility map is:

```text
uis/backoffice/
├── app/ or pages/
│   └── backoffice/inventory/
│       ├── products/                 # medical-supplies view
│       └── orders/
│           ├── index or page         # movement history
│           ├── inbound/              # delivery form
│           └── outbound/             # consumption form
├── components/inventory/             # shared tables, selectors, stock badges, forms
├── lib/inventory.ts                  # all inventory HTTP calls and normalization
└── types/ or colocated types         # request/response and normalized UI types
```

This tree is illustrative. Do not duplicate a `backoffice` path segment if the application already supplies it through `basePath`, routing groups, deployment configuration, or another established mechanism. The public browser URLs must still match the four required paths.

## Required Initial Analysis

Before implementation, inspect and document:

- whether the backoffice uses the App Router or Pages Router;
- how `/backoffice` is represented in source and deployment configuration;
- the existing authenticated layout/route guard and login path;
- where the JWT is stored and how authenticated requests currently obtain it;
- existing API-client/error abstractions that the inventory module should reuse;
- the implemented inventory OpenAPI schemas and actual sample responses;
- whether `user_uuid` is server-derived on mutations;
- existing form, select, table, badge, alert, loading, empty-state, and navigation components;
- current CSS/design-system conventions and accessible status colors;
- repository package manager, scripts, lint/type-check commands, and frontend test stack;
- environment-variable validation and `.env.local` ignore rules.

Produce a repository-grounded plan naming the concrete routes, source files, shared components, integration functions, types, tests, and validation commands before changing application code.

## Validation and Test Expectations

Use the existing frontend test tools and patterns. Test observable behavior and integration contracts rather than React or Next.js internals.

### Inventory integration module

Verify that:

- every request uses the configured base URL and correct `/inventory` path;
- every protected call carries the current bearer token;
- request payloads contain the expected API fields and omit UI-only state;
- successful responses are typed/normalized correctly;
- string `detail`, validation arrays, non-JSON bodies, empty bodies, and network failures become readable application errors;
- `401`, `400`, and unexpected `5xx` responses remain distinguishable;
- combined delivery/consumption payloads normalize into the history type.

### Medical-supplies page

Verify loading, populated, empty, and failed states; required HealthCore fields; numeric stock; stock-status labels; and row actions for delivery and consumption.

### Supply-delivery form

Verify product-name selection, valid payload submission, clinic/quantity validation, pending-state double-submit prevention, successful reset/confirmation, retained inputs after failure, and visible readable `400`/`500`/network errors.

### Supply-consumption form

Verify:

- product selection triggers the single-product stock request;
- stock loading and failure states affect submission appropriately;
- current stock updates when selection changes;
- stale requests cannot overwrite the latest selection;
- both allowed consumption types are available and no others are submitted;
- a quantity below or equal to stock is locally valid;
- a quantity above stock produces the client-side warning;
- backend HTTP `400` appears inline, retains correctable inputs, and triggers a stock refresh;
- successful submission produces confirmation and does not leave stale stock visible.

### Movement-history page

Verify loading, empty, success, and failure states; both movement types; product name; quantity; date; `user_uuid`; accessible type distinction; and absence of edit/delete actions.

### Authentication

Verify that each of the four routes redirects when unauthenticated, does not fetch protected inventory before authentication resolves, and uses the established signed-in path when authenticated. Verify existing `401` behavior without conflating it with inventory `400` errors.

### Proportional final checks

Run the narrowest relevant tests first, followed by the applicable frontend test suite, type check, lint check, and production build. Then perform a live smoke test against the running backend for all four routes and the success/error flows emphasized by the evaluator. Record exact commands and observed results in the active memory bank. Never claim a test or build passed unless it actually ran successfully.

## Evaluator-Critical Checks

The implementation will be explicitly evaluated for all of the following:

1. A dedicated inventory API module exists; inventory components contain no direct `fetch` calls.
2. Every protected inventory request carries the current user's `Authorization: Bearer <token>` header.
3. The medical-supplies page loads live API data, displays `current_stock`, and uses accessible visual stock indicators.
4. The delivery form submits correctly and visibly reports either confirmation or a readable failure on every outcome.
5. The consumption form reactively loads and displays current stock for the selected supply before submission.
6. The consumption form warns when the entered quantity exceeds displayed stock.
7. An outbound HTTP `400` message is visibly rendered inline rather than swallowed or shown as raw JSON.
8. The history view displays deliveries and consumptions with a clear distinction, product name, quantity, date, and `user_uuid`.
9. All four inventory pages redirect unauthenticated users to login.
10. Visible entity names, labels, and vocabulary follow the HealthCore context.

These are mandatory requirements, not optional examples.

## Acceptance Criteria

Part 2 is complete only when:

- The existing backoffice exposes the four required browser routes.
- All four routes use the existing authentication guard and redirect unauthenticated users to login without exposing protected content.
- One typed inventory integration layer owns all inventory HTTP calls and bearer-token handling.
- No inventory page or component calls `fetch` directly.
- The medical-supplies view shows live `MedicalSupply` data and computed stock with documented, accessible stock status.
- Each medical-supply row provides clear delivery and consumption actions.
- The delivery form uses a named supply selector, submits every required field, prevents duplicate submission, resets on success, and visibly reports success or failure.
- The consumption form uses a named supply selector, shows freshly loaded stock reactively, supports only `clinical_use` and `expiry_waste`, warns about locally excessive quantities, and handles backend stock conflicts inline.
- The movement-history view is read-only and shows all mandatory data for both deliveries and consumptions.
- Loading, empty, success, authentication, validation, network, and server-error states have deliberate user-visible behavior.
- HealthCore terminology is used throughout the UI; generic domain labels do not replace `MedicalSupply`, delivery, clinical use, or expiry waste concepts.
- The API base URL is environment-configured, `.env.local` remains uncommitted, and no token or secret is committed or exposed in logs/errors.
- Focused tests cover the evaluator-critical behaviors and applicable tests, type checks, lint checks, build, and live smoke flows pass with recorded evidence.
- Existing backoffice and public-site behavior outside this inventory section remains unchanged.

## Scope Boundaries

In scope:

- the four required inventory routes in the existing backoffice;
- a centralized inventory API integration module;
- authenticated live-data loading and submissions;
- HealthCore-specific tables, forms, labels, status indicators, and feedback;
- route protection through the existing authentication system;
- focused tests and only the shared component/configuration updates necessary for these views.

Out of scope unless a newer requirement adds it:

- building or changing the inventory backend contract except for a verified blocking defect;
- a new frontend application or repository;
- public-facing inventory pages;
- medical-supply creation, editing, or deletion UI;
- editing or deleting deliveries or consumptions;
- direct stock-adjustment UI;
- vendor, clinic, user, patient, procurement, billing, or reporting management;
- dashboards, charts, exports, barcode scanning, lot/serial tracking, reorder automation, pagination, search, or advanced filters;
- authentication redesign;
- unrelated backoffice refactors or visual redesign.

If integration reveals a backend contract mismatch or bug, document the exact mismatch and its evidence before expanding scope. Make the smallest coordinated correction only with appropriate authorization.

## Handoff Expectations

The implementation agent should begin with repository and live-API inspection, then produce a concrete plan. Keep the active project memory bank current with material plans, decisions, progress, backend-contract findings, validation results, blockers, and next steps.

Before finalizing Part 2:

1. Reconcile each of the four routes against its required loading, success, empty, authentication, and failure behavior.
2. Confirm all inventory requests flow through the integration module with bearer authentication.
3. Verify the reactive stock and outbound HTTP `400` flows against the live backend, not mocks alone.
4. Confirm history displays both movement types and every mandatory field.
5. Confirm HealthCore vocabulary and accessible non-color status cues across all views.
6. Run and record all applicable tests, type checks, lint checks, build, and smoke tests.
7. Update durable implementation memory only after the milestone is genuinely finalized.
