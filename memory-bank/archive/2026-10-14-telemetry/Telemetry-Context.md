# Telemetry Branch Context: HealthCore Telemetry Design Plan

## Purpose

This document is the implementation handoff for the **Telemetry branch only** of the HealthCore company project. The branch deliverable is a design package that tells a future developer exactly what telemetry the existing application should capture and how those events should be structured. It is a response to management's request for actionable business and technical information from the application.

This branch is **documentation only**. Do not add instrumentation, create a telemetry service, start a new server, change production behavior, or build a separate application. Work in the existing company monorepo and produce only the two required design artifacts:

```text
docs/telemetry/telemetry-plan.md
docs/telemetry/event-schemas.json
```

The plan must be precise enough that another developer can instrument the existing system without needing clarification.

## Authoritative References

Use only these two sources as the assignment authority for this branch:

1. [Designing your company's telemetry plan](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-telemetry-plan/README.md)
2. [CONTEXT — HealthCore: Telemetry Projects](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/06-telemetry-data-pipelines/telemetry/CONTEXT-healthcore.md)

The general telemetry-plan assignment defines the required process and deliverables. The HealthCore context defines the company-specific entities, mandatory events, properties, privacy boundaries, and business constraints. Where company-specific detail is required, use the HealthCore definitions exactly.

## Branch Outcome

Create a comprehensive telemetry design that:

- includes every mandatory HealthCore metric as the non-negotiable baseline;
- maps the complete inventory-management flow and identifies its instrumentation points;
- explores additional business and technical telemetry across the wider backoffice application;
- justifies every event with a testable hypothesis and a concrete decision;
- defines one consistent event envelope;
- defines a property allowlist and sensitivity treatment for every designed event;
- assigns and justifies a stream or batch delivery strategy for every event;
- documents throttling or debouncing for high-frequency events;
- records privacy, cost, risk, and exclusion decisions; and
- exports schemas in valid JSON that remain consistent with the Markdown plan.

The goal is a broad, implementation-ready catalogue, not a minimal checklist.

## Company Context

HealthCore operates 12 outpatient clinics across the United States and the United Kingdom:

- United States clinics are located in Texas, Florida, and Georgia.
- United Kingdom clinics are located in London and Manchester.

The inventory system manages clinical supplies used by these clinics, including commonly used medications, wound-care material, personal protective equipment, and consultation-room consumables. The existing production application is a FastAPI backend with authentication and a relational data model in Supabase.

The system enforces a non-negotiable stock rule: stock cannot be modified directly. Every stock change must occur through an inbound or outbound order and must be traceable to a staff user.

Management's immediate unanswered questions include:

- how many outbound orders are registered each day;
- which products accumulate the most validation errors;
- whether users are attempting to modify stock directly and being rejected;
- when minimum-stock threshold alerts occur most often;
- how many failed login attempts occur each day;
- which backoffice sections operators visit most; and
- where users abandon flows before completion.

The catalogue must support questions like these while also identifying other justified business and technical opportunities.

The telemetry designed here will later support the network operations dashboard and Dr. Okonkwo's monthly executive report. HealthCore's mandatory metrics must be designed so they can later be aggregated by clinic and country (`US` or `UK`). The future threshold alerts will also support Claire's compliance work, and low-stock conditions may be escalated to Marcus in Clinical Operations.

## Inventory Domain Vocabulary

Use these HealthCore meanings consistently in the plan and schemas:

| Entity | HealthCore meaning |
| --- | --- |
| `Product` | A clinical or consultation-room supply such as a box of nitrile gloves, 5 ml syringes, a flu vaccine, or surgical masks. A product has a category and, where applicable, an expiry date. |
| `InboundOrder` | Receipt of supplies from a vendor at a clinic. |
| `OutboundOrder` | Consumption of a supply during clinical care, associated with a department rather than a patient. |
| `clinic` | One of HealthCore's 12 clinics, identified by country (`US` or `UK`) and state or region. |
| `department` | The clinical area or service type, such as primary care, specialty care, chronic disease management, `general_consultation`, or `chronic_care`. It must never identify a patient. |

The allowed product categories defined by the HealthCore context are:

- `medication`
- `ppe`
- `consumable`
- `equipment`

For products that expire, the expiry date belongs on the `Product` model rather than only on an order. This is necessary for consistent computation of expiry telemetry across clinics.

## Regulatory and Data-Safety Boundary

HealthCore telemetry describes supplies, stock, staff interactions, application behavior, and operational processes. It must never describe patients.

No event field—including nested `properties`—may contain real or simulated protected health information or patient-identifying data. Prohibited content includes:

- patient names;
- medical-record identifiers;
- diagnoses; and
- any other value that could reasonably be interpreted as patient data.

When clinical context is needed for a supply-consumption event, record only a department or service type. Never record a patient identifier.

The design must explicitly identify any sensitive data or personally identifiable information that a proposed event could contain. For each such field, document how the value is anonymised or sanitised before emission. Property allowlists are mandatory and must prevent unapproved data from entering telemetry.

The privacy design must respect both HIPAA and UK GDPR.

## Mandatory HealthCore Metrics

All five events below are required from day one. They are the floor of the telemetry catalogue, not the complete catalogue. Preserve their `event_type` values exactly.

### `inbound_order_created`

- **Fires when:** a clinic registers receipt of supplies from a vendor.
- **Business hypothesis:** HealthCore needs to know what supplies are purchased, in what quantities, by which clinic, and from which vendor.
- **Decision enabled:** consolidate purchasing across clinics and negotiate improved vendor terms.

### `outbound_order_created`

- **Fires when:** a clinic records consumption of a supply in a department's care activity.
- **Business hypothesis:** HealthCore needs to know which supplies are consumed most and at what rate, segmented by clinic and department.
- **Decision enabled:** adjust automatic replenishment of critical supplies for each clinic.

### `stock_threshold_triggered`

- **Fires when:** a supply's stock at a clinic falls below its configured minimum.
- **Business hypothesis:** HealthCore needs to know how often clinics run short of critical supplies such as PPE or medication.
- **Decision enabled:** prioritise urgent restocking and escalate the condition to Marcus in Clinical Operations.

### `direct_stock_edit_rejected`

- **Fires when:** a user attempts to modify stock outside an order and the system rejects the attempt.
- **Business hypothesis:** HealthCore needs to know whether staff are trying to bypass supply-traceability controls.
- **Decision enabled:** reinforce training or permissions at the clinics where these attempts happen most.

### `supply_expiry_flagged`

- **Fires when:** a medication or material batch approaches its expiry date, for example within 30 days.
- **Business hypothesis:** HealthCore needs advance visibility into supplies that may become waste or a compliance risk.
- **Decision enabled:** prioritise use or controlled disposal before expiry.

### Minimum inventory-event properties

In addition to the standard event envelope, every inventory event must include the first five fields below. Include `department` only where it applies:

| Property | Requirement |
| --- | --- |
| `clinic_id` | Identifies the clinic associated with the event. |
| `country` | Must be `US` or `UK`. |
| `product_id` | Identifies the affected supply product. |
| `product_category` | Must be `medication`, `ppe`, `consumable`, or `equipment`. |
| `quantity` | Records the relevant supply quantity. |
| `department` | Include only where applicable. It identifies a clinical area or service, never a patient. |

The plan and JSON schemas must preserve these minimum fields, determine whether `department` applies to each event, and remain faithful to the privacy restrictions.

## Phase 1: Exhaustive Catalogue of Data Opportunities

### Map the inventory flow

Document the flow from an authenticated user's entry into the inventory system through successful creation of an inbound or outbound order. Identify at least five instrumentation points in that flow.

The inventory analysis must include:

- inbound orders;
- outbound orders;
- failed validations;
- rejected attempts to modify stock directly; and
- minimum-stock threshold activations.

It must also cover the mandatory expiry event and the HealthCore product, clinic, country, category, quantity, and department context needed by the mandatory metrics.

### Explore the rest of the backoffice

Do not stop at inventory or at the five mandatory events. Build a broad catalogue of well-grounded opportunities across application areas users or internal processes touch. The source specifically calls for exploration of:

- authentication, including login attempts, failed logins, credential failures, and expired sessions;
- performance, including API response times and application load times;
- uncaught frontend errors;
- navigation, including which sections operators visit most; and
- user flows that are abandoned before completion.

Additional opportunities may be included when they are supported by a clear hypothesis and decision. Do not add events merely because data is available.

### Justify every event

Every catalogue entry must complete this reasoning chain:

> We capture `[event_type]` because we need to know `[hypothesis]`, which allows us to make the decision `[concrete decision]`.

Discard any proposed event that cannot complete the sentence with a meaningful hypothesis and decision.

Classify every catalogue entry as one of:

- **mandatory** — one of the five HealthCore events; or
- **identified opportunity** — an additional event proposed through the application review.

The catalogue should make its categories visible, such as business/inventory, authentication, performance, errors, and navigation.

## Phase 2: Event Envelope and Event Schemas

### Standard event envelope

Every event must use the same envelope and include at least:

| Field | Requirement |
| --- | --- |
| `eventId` | Unique event identifier. |
| `timestamp` | Event time in ISO 8601 format. |
| `sessionId` | Identifier for the relevant application session. |
| `userId` | Identifier for the relevant user. |
| `event_type` | Consistent `entity_action` taxonomy. |
| `schemaVersion` | Version of the event schema. |
| `requestId` | Correlation identifier used to join frontend activity, backend activity, and logs. |
| `properties` | Event-specific payload restricted by the event's allowlist. |

Use consistent action verbs across the taxonomy. Source examples include:

- `inbound_order_created`
- `stock_threshold_triggered`
- `direct_stock_edit_rejected`
- `session_expired`
- `api_latency_recorded`

### Required schema coverage

Define complete schemas for:

- all five mandatory HealthCore events; and
- at least eight additional events from the catalogue.

The additional events must span at least three distinct categories, such as business/inventory, authentication, performance, errors, and navigation. This is a minimum coverage requirement; the overall catalogue is expected to be broader when additional events meet the hypothesis-and-decision rule.

For every designed event, document:

- exact `event_type`;
- description and firing condition;
- classification as mandatory or identified opportunity;
- category;
- hypothesis;
- decision enabled;
- every allowed property;
- each property's type;
- whether each property is required or optional;
- each property's description;
- whether the event or property contains sensitive data or PII; and
- the anonymisation or sanitisation treatment for any sensitive value.

### Property allowlists

Every event must define an explicit allowlist of permitted keys in `properties`. Data not named by the allowlist must not be emitted. The allowlist is part of the privacy and leakage-prevention design, not optional narrative documentation.

### JSON schema artifact

Export the event definitions to `docs/telemetry/event-schemas.json` using either:

- JSON Schema draft-07; or
- a documented custom validation structure.

The file must be valid JSON, must be suitable for validation, and must remain consistent with `docs/telemetry/telemetry-plan.md`.

## Phase 3: Delivery Strategy

Assign every designed event to either **stream** or **batch** processing and justify the choice.

- Choose **stream** when the operational or business decision requires data within seconds.
- Choose **batch** when periodic processing is sufficient.

Do not justify the choice using technical preference alone. Tie it to the urgency of the decision or the operational need for rapid detection.

For any high-frequency event, document an appropriate throttle or debounce strategy. The plan must also contain a risks and exclusions section that identifies:

- events considered and discarded, with the reason for each exclusion;
- data deliberately not captured for privacy reasons; and
- data deliberately not captured because its collection cost is not justified.

## Suggested Data Scenarios for Future Telemetry Work

The HealthCore context suggests the following minimum data set for later capture, storage, reporting, or validation work:

- 8–10 distinct supply items spanning all four product categories;
- 3 clinics, including at least one US clinic and one UK clinic;
- 15–20 inbound orders distributed across those clinics;
- 15–20 outbound orders associated only with a department and never with a patient;
- at least 2 cases that trigger `stock_threshold_triggered`; and
- at least 1 case that triggers `supply_expiry_flagged`.

These scenarios inform schema completeness and future usability. This branch remains documentation-only and must not add seed data or instrumentation.

## Required Structure of `telemetry-plan.md`

The Markdown plan must be organized clearly enough for implementation by another developer. It must include, at minimum:

1. scope and HealthCore business context;
2. inventory-flow map and instrumentation points;
3. exhaustive event-opportunity catalogue;
4. mandatory-versus-identified classification;
5. hypothesis and decision for every event;
6. standard Event Envelope;
7. per-event schema and property allowlist;
8. sensitive-data and PII analysis;
9. stream-versus-batch decision and justification for every event;
10. throttle/debounce strategy for high-frequency events; and
11. risks, discarded events, privacy exclusions, and cost exclusions.

The plan and JSON file must use the same event names, fields, types, required/optional rules, and sensitivity treatments.

## Acceptance Criteria

This branch is complete only when all of the following are true:

- `docs/telemetry/telemetry-plan.md` exists.
- `docs/telemetry/event-schemas.json` exists and is valid JSON.
- All five mandatory HealthCore metrics are present and clearly marked mandatory.
- The inventory flow contains at least five instrumentation points and covers direct stock-edit rejection, validation failures, and threshold activation.
- The catalogue broadly covers business and technical telemetry rather than stopping at the mandatory minimum.
- Every event has a meaningful hypothesis and concrete decision.
- The standard envelope contains `eventId`, ISO 8601 `timestamp`, `sessionId`, `userId`, `event_type`, `schemaVersion`, `requestId`, and `properties`.
- Every `event_type` follows a consistent `entity_action` taxonomy.
- Complete schemas exist for all mandatory events and at least eight additional events across at least three categories.
- Every event has an explicit property allowlist.
- Inventory properties preserve HealthCore's identifiers, category values, and `US`/`UK` country values.
- Department is used only as non-patient clinical context.
- No real or simulated patient data or PHI appears anywhere, including examples and test-like data.
- Sensitive data and PII are identified with anonymisation or sanitisation rules.
- Every stream/batch choice is justified by decision urgency or operational need.
- High-frequency events have a documented throttle/debounce strategy where applicable.
- Risks and exclusions explain what will not be captured and why.
- The Markdown plan and JSON schemas are internally consistent and implementation-ready.

## Out of Scope

Do not perform any of the following on this branch:

- instrument application code;
- create or deploy a telemetry pipeline;
- create a new telemetry server or repository;
- modify authentication, inventory, or database behavior;
- add seed records;
- create dashboards, alerts, or executive reports;
- store, process, or simulate patient data; or
- expand the assignment beyond the two required design artifacts.

## Submission Requirements

After the two artifacts are complete, the assignment calls for a pull request against the monorepo's main branch titled:

```text
docs: telemetry design plan
```

The pull-request description must state:

- the total number of designed events;
- how many events are mandatory and how many are identified opportunities;
- the categories covered; and
- one sentence describing the hardest design decision.

Creating the pull request is not part of this context-preparation task. It is recorded here so the implementation agent can prepare the deliverables for the required submission format.
