# HealthCore Digital - Milestone 9 Part 1 Cursor Implementation Context

## Purpose of this document

This is the implementation contract for **Milestone 9, Part 1 only: Agentic RFP Workflow - Intake and Routing**. It combines the generic 4Geeks Part 1 milestone with the HealthCore-specific briefing and the architecture already present in this repository.

The current documentation task does **not** authorize implementation, dependency installation, schema creation, branch creation, commits, pushes, pull requests, deployment, or production-data changes. The user will provide this file to Cursor in a later build session. In that later session, Cursor must inspect the current checkout, follow `AGENTS.md` and scoped repository rules, make the smallest implementation that satisfies this contract, test it, and stop before Git or deployment actions unless the user explicitly requests them.

Parts 2 and 3 are not part of this implementation. Part 1 must create durable contracts that those later parts can extend without re-parsing the original PDF or redesigning ticket state.

## Source authority and conflict resolution

Use these sources in this order:

1. The user's direct instructions and repository `AGENTS.md`.
2. The HealthCore Milestone 9 briefing: <https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/09-agentic-workflows/healthcore-BRIEFING.md>.
3. The Part 1 milestone README: <https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-agentic-workflows-orchestrate/README.md>.
4. Current repository code, active memory-bank files, scoped `.agents/rules/`, and existing implementation conventions.

Where the generic README says `uis/backoffice`, use this repository's actual internal application, **`uis/web`**, and place the feature under its protected backoffice routes. Do not create a new frontend app. Where generic examples suggest a new backend, use the existing FastAPI application in `services/api`. Where the briefing or README conflicts with a convenient shortcut, the HealthCore privacy and persistence requirements win.

## Business goal

HealthCore receives institutional requests for occupational health contracts, corporate wellness programs, and referral partnerships. HealthCore has no traditional Sales department. **Tom Callahan, Revenue Cycle Director, acts as the Sales/ticket owner** for these opportunities.

Today a proposal takes about three weeks because Revenue Cycle must coordinate input from Clinical Operations and Compliance. Part 1 must turn each uploaded PDF into a pollable ticket, decide whether the document is a legitimate HealthCore RFP, safely extract metadata and readability measurements, split analysis into department-specific workstreams, and synthesize a Sales-facing intake result that says what is needed and whom to ask.

Part 1 ends after intake and routing. It does not draft proposal sections, run generator-evaluator loops, request human approvals, arbitrate Part 3 conflicts, or generate a final proposal document.

## HealthCore facts and fixed department registry

Use exactly these department identifiers. Do not create agents or database records for generic departments such as `sales`, `legal`, `finance`, `operations`, or `it`.

| `department_id` | Display name | Named owner | Part 1 responsibility |
| --- | --- | --- | --- |
| `revenue` | Revenue Cycle | Tom Callahan | Owns the ticket; identifies financial terms, currency, payment structure, contract term, budget gaps, and commercial questions. |
| `clinical` | Clinical Operations | Dr. Marcus Reid | Identifies clinic, staffing, capacity, service, schedule, and clinical-feasibility requirements without handling patient cases. |
| `compliance` | Compliance and Data Governance | Claire Whitfield | Identifies HIPAA/UK GDPR, BAA/DPA, data-security, privacy, and PHI concerns. This department is mandatory for every accepted RFP. |

The department registry should be application-owned typed data, not an LLM invention. The orchestrator may select only from these identifiers. `compliance` must always be present on accepted RFPs. An unknown department named in a PDF must become an open question or be mapped to the closest allowed responsibility only when that mapping is unambiguous; it must never create a fourth worker dynamically.

## Non-negotiable privacy invariant

HealthCore operates under HIPAA in the US and UK GDPR in the UK. **No patient name, diagnosis, patient identifier, or other PHI may appear in any event, database table, API response, UI ticket, log, trace, task result, generated Markdown artifact, prompt capture, test evidence, or generated document. This includes fictional and illustrative patient data.**

The uploaded PDF is user-supplied input and must be stored as required, but it must be treated as a restricted raw artifact:

- Save it under `data/raw/` using an opaque server-generated ticket identifier, never the original filename or client/patient text.
- Do not log the file contents, original filename, extracted text, prompts, model output, or client contact details.
- Do not provide a public/raw-file download route in Part 1.
- Ensure the backend and worker see the same `data/raw/` volume/path.
- Git-ignore runtime uploads and derived artifacts. Do not commit curriculum PDFs to `data/raw/`.
- Conversion may use a controlled temporary file or in-memory value. Never persist unredacted Markdown when PHI is detected.
- Detect sensitive content before any classifier, orchestrator, worker, synthesizer, memory system, RAG component, MCP tool, or external model receives the text.
- Reuse and extend existing privacy/redaction patterns where appropriate, but keep the RFP graph independent from the existing staff compliance agent.

For a PDF that otherwise looks like an RFP but contains a clinical case summary or patient details:

1. Convert it in a controlled local step so it can be inspected.
2. Detect the sensitive content before any agent call.
3. Do not echo or persist the offending text.
4. Stop normal agent processing.
5. Record only safe booleans and reason codes such as `contains_phi=true`, `reason_code="phi_detected"`, and `requires_compliance_review=true`.
6. Use the Part 1 terminal lifecycle without inventing `waiting_for_approval`; the recommended outcome is `discarded` with the safe PHI reason code because the document cannot advance through intake.
7. Show Revenue Cycle a fixed safe message explaining that protected information was detected and the document requires a privacy-safe resubmission/Compliance handling. Do not show a snippet.

This PHI gate is deterministic application policy. An LLM may not override it.

## Scope

### Required in Part 1

- An authenticated ticket-mode RFP page inside `uis/web`.
- PDF upload through the existing FastAPI backend.
- Immediate ticket creation and quick `202 Accepted` response.
- Opaque raw PDF storage under `data/raw/`.
- PostgreSQL/Supabase persistence for tickets, metadata, department key aspects, and the Part 2 handoff. TinyDB and JSON files are not acceptable sources of truth.
- Asynchronous execution using the repository's existing Celery/Redis infrastructure.
- PDF-to-Markdown conversion before any agent reads the document.
- A pre-agent PHI/privacy gate.
- A classifier agent that accepts formal and informal institutional requests and rejects non-RFP sales/vendor material.
- Metadata extraction and readability metrics.
- A dedicated LangGraph-style `rfp_intake` graph under `data/pipelines/rfp_intake/`.
- Separate orchestrator, parallel department workers, and synthesizer responsibilities.
- Per-department `key_aspects`, open questions, safe source references, and owner/contact mapping.
- A durable handoff containing `ticket_id` plus the synthesizer/workstream payload for Part 2.
- Pollable ticket status and a Sales-facing intake result.
- Focused pipeline, API/task, persistence, and UI tests.
- Manual verification with all three supplied PDFs through the UI.

### Explicitly out of scope

- Proposal-section generation.
- Generator-evaluator loops.
- Readability/relevance/compliance evaluation of proposal drafts.
- Human approval controls or `waiting_for_approval`.
- Part 3 arbitration and conflict resolution.
- Final proposal or PDF generation.
- Adding a new API service or new frontend application.
- Adding RFP nodes to the existing knowledge/compliance agent graph.
- RAG ingestion of the RFP, Qdrant indexing, or long-term agent memory.
- MCP tools for RFP intake.
- Email delivery, CRM integration, procurement submission, or client notification.
- Production deployment or production Supabase changes without explicit authorization.

## Existing repository baseline to preserve

Cursor must verify these paths before editing because the repository may have changed:

| Area | Current implementation to preserve or extend |
| --- | --- |
| Internal UI | `uis/web`, protected by its existing auth provider and rendered through `BackofficeShell`. Backoffice pages already live under `uis/web/src/app/(protected)/backoffice/`. |
| HTTP API | One FastAPI app at `services/api/app/main.py`; routers live under `services/api/app/routers/`. Do not create another service. |
| Authentication | Existing JWT bearer flow and `get_current_user`. RFP routes must require staff authentication. |
| Database | `services/api/app/database.py` provides SQLModel sessions through `DATABASE_URL`; local tests use isolated SQLite, while the real target for this feature is PostgreSQL/Supabase. |
| Background work | Existing Celery app at `services/api/app/celery_app.py`, Redis broker/result backend, worker service, retry conventions, task status patterns, and dead-letter storage. Extend these instead of adding a second queue framework. |
| Pipelines | Existing `data/pipelines/` import path is made available to the API and worker. The RFP graph belongs in `data/pipelines/rfp_intake/`. |
| Existing agent | `services/api/app/agent/` is the staff-facing compliance/knowledge agent with guardrails and memory. Do not add RFP nodes to it or reuse its conversation state. |
| Frontend API helpers | `uis/web/src/lib/apiClient.ts` provides authenticated fetch, timeouts, status mapping, and safe error handling. Reuse its conventions. |
| Error handling | User-facing errors are sanitized. Raw exception details, provider messages, stack traces, PDF text, and model output stay server-side and must also be sanitized there. |

The current Compose worker does not yet mount `data/raw/`. The implementation must make raw uploads accessible at the same path to both API and worker, using a narrowly scoped volume such as `./data/raw:/app/data/raw`. Do not expose that directory through the web server.

## Required repository layout

Use this shape unless the current code establishes an equally clear convention:

```text
data/
├── raw/                              # runtime PDFs, gitignored; opaque names
└── pipelines/
    └── rfp_intake/
        ├── __init__.py
        ├── graph.py                  # dedicated graph and routing
        ├── state.py                  # typed graph state and reducers
        ├── schemas.py                # structured agent I/O, no ORM imports
        ├── conversion.py             # PDF -> Markdown boundary
        ├── privacy.py                # pre-agent content gate/redaction contract
        ├── classifier.py
        ├── metadata.py
        ├── orchestrator.py
        ├── workers.py
        ├── synthesizer.py
        └── service.py                # one callable pipeline entry point
services/api/app/
├── rfp/
│   ├── __init__.py
│   ├── models.py                     # SQLModel persistence models
│   ├── schemas.py                    # HTTP DTOs
│   ├── repository.py                 # DB reads/writes and transitions
│   └── service.py                    # upload intake and query orchestration
├── routers/
│   └── rfp.py                        # thin authenticated HTTP boundary
└── tasks/
    └── rfp_intake.py                 # thin Celery wrapper around pipeline
tests/pipelines/
└── rfp_intake/
    ├── test_classifier.py
    ├── test_workers.py
    ├── test_privacy.py
    └── test_graph.py
services/api/tests/
├── test_rfp_api.py
├── test_rfp_task.py
└── test_rfp_persistence.py
uis/web/src/
├── app/(protected)/backoffice/rfp/
│   ├── page.tsx
│   └── [ticketId]/page.tsx           # optional if list/detail is split
├── components/rfp/
└── lib/rfp.ts
```

Do not force file proliferation if a smaller structure remains clear and testable. The strict boundaries are: HTTP under `services/`, pipeline under `data/pipelines/rfp_intake/`, standalone CLI under `scripts/` only if useful, and UI inside `uis/web`.

## Persistence model

Use SQLModel with `DATABASE_URL`. PostgreSQL/Supabase is the deployed source of truth. Tests may override the URL with a temporary SQLite database following existing test patterns. Register all new models with `init_db()` so local/test metadata creation includes them. Do not use TinyDB, the Celery result backend, or JSON files as the durable RFP store.

Use UUIDs or similarly opaque identifiers. Store JSON only for bounded structured fields; validate it through Pydantic models before writing or returning it.

### Ticket

Minimum fields:

| Field | Contract |
| --- | --- |
| `ticket_id` | Opaque primary identifier returned to the UI and carried into Parts 2/3. |
| `rfp_id` | Nullable opaque RFP identifier; populated for an accepted/parsed RFP. |
| `status` | Part 1 lifecycle enum: `analyzing`, `discarded`, or `intake_complete`. |
| `processing_state` | Operational state separate from business lifecycle, for example `queued`, `running`, `retrying`, `failed`, `succeeded`. This lets the UI report worker failure truthfully without inventing a Part 2/3 ticket status. |
| `raw_pdf_path` | Relative opaque path such as `data/raw/<ticket_id>.pdf`; never an original filename. |
| `task_id` | Nullable Celery task id for diagnostics and safe polling/reprocessing. |
| `outcome_reason_code` | Nullable safe code such as `not_an_rfp`, `phi_detected`, `conversion_failed`, or `processing_failed`; never raw exception text. |
| `contains_phi` | Boolean only. Never store the matched value. |
| `requires_compliance_review` | Boolean. True for the improper-PHI critical case. |
| `intake_summary` | Validated JSON synthesizer payload used as the Part 2 handoff. Null until complete. |
| `created_by_user_id` | Authenticated owner/audit subject from the existing user identity. Do not store unnecessary profile data. |
| `created_at`, `updated_at` | Timezone-aware UTC timestamps. |

Ticket transitions must be guarded and idempotent. A retry must not create another ticket, another RFP, or duplicate department sections.

### RFP metadata

Minimum fields:

| Field | Contract |
| --- | --- |
| `rfp_id`, `ticket_id` | Opaque identifiers and one-to-one ticket relationship. |
| `client_name` | Institutional client only. Null when missing; never infer a name. |
| `client_country` | Strict `US` or `UK`; null/unknown causes an open question rather than a guess. |
| `program_type` | Controlled values where confidently mapped: `occupational_health`, `corporate_wellness`, `referral_network`; allow a safe `other_institutional` if the request is valid but not one of these. |
| `covered_population` | Non-negative institutional employee/student count or null. It is not a patient count. Never invent it. |
| `deadline` | Proposal response deadline when explicit, otherwise null. Do not confuse a requested service start date with the proposal deadline. |
| `budget_range` | Structured or normalized safe value only when present; otherwise null. Do not fabricate pricing. |
| `departments_needed` | Unique ordered list containing only allowed department ids. `compliance` is mandatory. |
| `currency` | Derived deterministically from country: `USD` for US, `GBP` for UK; null if country is unresolved. |
| `flesch_reading_ease` | Readability output or null with safe metric error code. |
| `flesch_kincaid_grade` | Readability output or null. |
| `gunning_fog` | Readability output or null. |
| `word_count`, `sentence_count`, `character_count`, `page_count` | Bounded non-negative document-cost indicators. |
| `classification_confidence` | Optional bounded numeric confidence if the provider supports it; it may not replace deterministic validation. |
| `created_at`, `updated_at` | Timezone-aware UTC timestamps. |

Readability metrics anticipate processing cost; they are not a pass/fail literary grade. Metric failure should not automatically reject a legitimate RFP. Record a safe metric status and continue when the document is otherwise usable.

### DepartmentSection for Part 1

Create one row per required department with a unique `(ticket_id, department_id)` constraint.

| Field | Part 1 contract |
| --- | --- |
| `ticket_id`, `department_id` | Parent ticket and one of `revenue`, `clinical`, `compliance`. |
| `owner_name` | Prefer resolving from the fixed registry at response time; if persisted, validate it against the registry. |
| `key_aspects` | Validated JSON list of concise factual requirements relevant to that department. |
| `open_questions` | Validated JSON list of missing/ambiguous facts that the department must resolve. |
| `source_references` | Safe page/section labels or bounded excerpts that contain no PHI. Do not store the whole document. |
| `contains_phi` | Boolean, default false. No section may advance with true. |
| `created_at`, `updated_at` | Timezone-aware UTC timestamps. |

The briefing also defines `draft_content`, `evaluation_results`, `approval_status`, `approver`, and `approved_at` for later parts. Cursor may include nullable columns now if that is necessary for a stable migration, but Part 1 must not populate or expose draft/evaluation/approval behavior.

### Part 2 handoff payload

Persist a validated synthesizer payload before changing the ticket to `intake_complete`. It must contain at least:

```json
{
  "ticket_id": "opaque-id",
  "rfp_id": "opaque-id",
  "client_country": "US",
  "currency": "USD",
  "departments": [
    {
      "department_id": "revenue",
      "owner": "Tom Callahan",
      "key_aspects": ["..."],
      "open_questions": ["..."]
    }
  ],
  "requires_compliance": true,
  "contains_phi": false
}
```

The exact serialized shape may evolve, but Part 2 must be able to start from `ticket_id` and this persisted structure without reading or converting the PDF again. `status="intake_complete"` is the durable ready flag.

## Ticket lifecycle and failure truthfulness

Use the briefing's Part 1 business statuses only:

```text
upload accepted -> analyzing
analyzing -> intake_complete   (valid RFP, all workstreams persisted)
analyzing -> discarded         (classifier rejects or PHI gate blocks)
```

Do not use `drafting`, `under_evaluation`, `needs_human_review`, `waiting_for_approval`, or `done` in Part 1.

Operational queue state is separate:

```text
queued -> running -> succeeded
               \-> retrying -> running
               \-> failed
```

During retry the business status remains `analyzing`. After exhausted infrastructure failure, preserve the ticket and raw artifact, set `processing_state="failed"`, store only a safe reason code, and let the UI show a fixed failure/retry message. Do not mislabel a system failure as `not_an_rfp`. A later authenticated reprocess action may enqueue the same ticket idempotently; it must not create a new ticket.

Persist the final payload and department rows transactionally before changing status to `intake_complete`. The UI must never see `intake_complete` with missing workstreams.

## HTTP API contract

Use an authenticated router in the existing API. Route names may follow existing conventions, but a coherent contract is:

### `POST /rfp/tickets`

- Accept `multipart/form-data` with exactly one PDF.
- Require existing JWT authentication.
- Validate extension, content type, PDF magic bytes, non-empty content, and a documented maximum size before durable save/enqueue.
- Stream to disk; do not read an unbounded file into memory.
- Generate the ticket id server-side and store as `data/raw/<ticket_id>.pdf`.
- Create the `analyzing`/`queued` ticket before publishing work.
- Enqueue the existing Celery worker with only safe identifiers/paths, not PDF text.
- If broker publication fails, preserve a truthful failed/queue-unavailable record or roll back both DB row and file consistently. Do not leave an invisible orphan.
- Return quickly with `202 Accepted`:

```json
{
  "ticket_id": "opaque-id",
  "status": "analyzing",
  "processing_state": "queued"
}
```

Do not run conversion or any LLM call in the request lifecycle.

### `GET /rfp/tickets`

- Return a bounded/paginated list for authenticated staff.
- Include safe summary fields only: ids, business/processing status, institutional client name when known, country, program type, timestamps, and safe reason code.
- Never return raw paths as download URLs, extracted text, prompts, or model output.

### `GET /rfp/tickets/{ticket_id}`

- Return current ticket state, metadata/readability when available, and department/synthesizer results when complete.
- For `analyzing`, return pollable state without pretending results exist.
- For `discarded`, return a fixed safe explanation based on reason code.
- For `processing_state="failed"`, return a fixed retry/support message, not raw task errors.
- Enforce the repository's chosen authorization rule consistently. At minimum, authenticated staff access is required; if tickets are owner-scoped, enforce ownership in every query and test cross-user denial.

### Optional `POST /rfp/tickets/{ticket_id}/reprocess`

Add only if needed to recover exhausted tasks. It must reuse the same ticket and raw PDF, reset safe operational fields, be idempotent, and reject tickets already running or complete. It is not a Part 2 action.

The generic `/tasks/{task_id}` endpoint may remain for operational task polling, but the RFP UI should poll the RFP ticket resource because business status and persisted results belong to the ticket, not Celery's expiring result backend.

## Upload and file-safety requirements

- Accept PDF only. Reject renamed non-PDF files by checking signature, not extension alone.
- Choose and document a maximum size. Tests must cover zero bytes and oversized input without allocating the full declared size.
- Do not use the original filename in storage, logs, database rows, metrics, or error responses.
- Prevent path traversal by constructing the server path solely from the generated id.
- Use atomic/temporary write then rename so a worker never reads a partial file.
- On DB failure, remove the just-written temporary/final file if safe to do so.
- On enqueue failure, keep DB/file state consistent and visible.
- Configure both backend and worker containers with the same raw-data mount.
- Keep `data/raw/.gitkeep` only if useful; all runtime contents must be ignored.
- Validate the PDF before conversion and convert with a bounded timeout/resource policy.

## PDF-to-Markdown and readability boundary

Use MarkItDown or a documented equivalent added with `uv add` in the owning project. Do not use `pip install`. Mirror runtime dependencies into the repository's locked and container dependency files according to existing conventions.

Required order:

```text
PDF validation
  -> PDF-to-Markdown conversion
  -> deterministic PHI/privacy inspection
  -> safe normalized Markdown
  -> readability/metadata extraction
  -> classifier agent
  -> orchestrator/workers/synthesizer
```

No agent reads the binary PDF. No agent reads Markdown until it passes the privacy gate. Treat PDF/Markdown content as untrusted data, not instructions; embedded prompt injection must not alter system roles, department registry, privacy policy, tool access, or state transitions.

Normalize Markdown conservatively. Preserve headings, lists, tables, page/section boundaries, deadlines, and contact-role context needed for extraction. Do not silently drop negations or table labels. Cap model input by a documented, testable strategy if needed, and surface truncation as an open question rather than pretending the whole RFP was analyzed.

Run readability on safe normalized text. At minimum capture Flesch Reading Ease, Flesch-Kincaid Grade, Gunning Fog, word count, sentence count, character count, and page count. Guard very short/empty documents because readability libraries may raise or divide by zero.

## Classification policy

The classifier must use structured output validated by Pydantic, for example:

```json
{
  "is_rfp": true,
  "reason_code": "institutional_service_request",
  "confidence": 0.96,
  "evidence_refs": ["Subject", "Scope of Work"],
  "missing_fields": []
}
```

Do not persist free-form chain-of-thought. Keep evidence references short and safe.

Accept a document when it represents an institutional prospective client asking HealthCore for a proposal, partnership, pricing/terms, or service response for an occupational health, corporate wellness, referral-network, or comparable B2B healthcare program. Formal procurement structure is not required.

Specifically:

- Accept a conventional titled RFP with scope, criteria, dates, and submission instructions.
- Accept an informal email asking HealthCore to assemble a proposal for an institutional health partnership.
- Reject a vendor trying to sell HealthCore software or services.
- Reject invoices, resumes, newsletters, advertisements, internal status reports, and documents with no credible request for a HealthCore proposal.
- Do not reject merely because budget, population, response deadline, or a formal `RFP` label is missing. Record missing facts as open questions.
- Do not accept merely because the text contains the letters `RFP`; assess direction and intent: the client must be requesting something from HealthCore.
- A malformed/unknown model response fails closed to a safe processing error/review path, not an invented classification.

Classification rejection stops orchestration and marks the ticket `discarded` with a safe reason code. One rejected ticket must not stop other tickets.

## Metadata extraction rules

Use structured output with strict types and application validation. Do not let the model set database status directly.

- `client_name`: extract the institution requesting a proposal, not a vendor pitching HealthCore.
- `client_country`: only `US` or `UK` when supported by the document. Do not infer country solely from currency unless policy explicitly allows it.
- `program_type`: normalize only when clearly supported.
- `covered_population`: institution-level employee/student volume only. Never extract patient-level counts as a business population.
- `deadline`: proposal response/submission deadline only. Keep requested launch/start dates in key aspects, not this field.
- `budget_range`: preserve amount, range, and currency only when present. Otherwise null.
- `departments_needed`: allowed ids only; always include `compliance` on accepted RFPs.
- `currency`: derive deterministically after country validation: US -> USD, UK -> GBP.
- Missing or conflicting facts become open questions. Never use model world knowledge to fill them.

## Dedicated graph and agent responsibilities

Build a dedicated LangGraph (or the equivalent already used here) named for `rfp_intake`. Do not attach it to `services/api/app/agent/graph.py`.

Suggested flow:

```text
load ticket/raw artifact
  -> convert PDF to Markdown
  -> privacy gate
      -> PHI blocked -> persist safe discarded outcome -> end
  -> readability + metadata extraction
  -> classifier
      -> invalid -> persist discarded outcome -> end
  -> orchestrator
      -> parallel revenue worker
      -> parallel clinical worker
      -> parallel compliance worker (always)
  -> synthesizer
  -> validate complete safe payload
  -> transactional persistence
  -> mark intake_complete
  -> end
```

The graph state should be typed and carry references/structured values rather than raw durable content. A workable state includes:

- `ticket_id`, `raw_pdf_path`
- transient `safe_markdown`
- `contains_phi`, safe privacy reason codes
- readability metrics
- validated RFP metadata
- classifier result
- orchestrator work items
- a reducer-managed list/map of department results
- synthesizer payload
- bounded safe errors

Do not checkpoint raw Markdown, prompts, responses, or PHI. If graph checkpointing is used, persist only safe structured state or use an in-memory test saver and rely on the ticket database for durable lifecycle state.

### Orchestrator

The orchestrator reads only safe Markdown and validated metadata. It creates typed work items containing:

- one allowed `department_id`;
- shared validated metadata;
- only department-relevant extracts/references;
- explicit missing fields/open questions;
- fixed owner/role metadata from the registry.

It must not give every worker the whole document by default. It cannot remove `compliance`, create unknown departments, invent volume/budget/capacity, or resolve PHI/regulatory policy.

Use actual parallel fan-out/fan-in supported by the graph (`Send`, parallel branches, or equivalent), not a single loop masquerading as multiple agents.

### Department workers

Each worker has a distinct system role and structured output. It returns factual `key_aspects`, `open_questions`, and safe source references. It must not draft a proposal.

**Revenue worker** should identify:

- commercial structure, contract term/renewal, pricing/budget information, payment requirements, currency, submission deadline/instructions, evaluation criteria relevant to pricing, and missing commercial facts;
- institutional volume only when explicitly supplied;
- no invented pricing, discount, payment schedule, or budget.

**Clinical worker** should identify:

- requested services, clinics/locations, delivery model, staffing cadence, capacity considerations, covered population, target start dates, and clinical feasibility questions;
- no patient case details, diagnoses, or invented staffing/capacity commitments.

**Compliance worker** must always run for an accepted RFP and should identify:

- country/jurisdiction, required data agreement, privacy/data-security requirements, regulatory gaps, and whether sensitive content was blocked;
- US requires a BAA-related key aspect; UK requires a DPA/UK GDPR-related key aspect;
- no legal clause drafting in Part 1 and no claim of approval.

### Synthesizer

The synthesizer combines validated worker results into a concise Sales-facing workstream structure. It must:

- include every required department exactly once;
- name the fixed owner/contact for each workstream;
- preserve contradictions or missing facts as open questions rather than choosing a convenient answer;
- enforce country/currency and BAA/DPA consistency;
- reject a payload with PHI, unknown departments, missing compliance, duplicated departments, or invented facts;
- produce no proposal prose;
- persist the Part 2 handoff before the ticket is completed.

If workers contradict one another, the synthesizer records a structured conflict/open question. Agent consensus is not authority. Part 3 arbitration is out of scope.

## Model/provider behavior

- Reuse the repository's existing LLM base URL/key conventions where appropriate; do not hard-code or guess model ids.
- Keep model calls behind injectable interfaces so tests use deterministic fakes and require no network or credentials.
- Use separate application-owned prompts for classifier, orchestrator, workers, and synthesizer.
- Send document content as delimited untrusted data in the user/data role, never as system instructions.
- Require structured output and validate every response. Unknown enums, extra departments, missing mandatory fields, invalid confidence, or oversized strings must fail safely.
- Use explicit timeouts, bounded retries for transient provider failures, and no retry for deterministic validation/classification outcomes.
- Do not log prompts, document text, responses, contacts, or provider payloads.

## Async execution and idempotency

Reuse Celery/Redis. Add a thin task wrapper such as `app.tasks.rfp_intake` and include it in the existing Celery configuration. The task should receive `ticket_id`, then load the opaque path from the database; do not put extracted document content on Redis.

Use the existing task conventions for retries, soft/hard time limits, sanitized errors, and broker failures, adapted to RFP processing. Classifier rejection and PHI blocking are successful business outcomes, not Celery failures. Conversion/provider/database/network timeouts may be retryable. Schema violations and missing raw artifacts are permanent unless explicitly repairable.

Required idempotency behavior:

- The same task retry updates the same ticket.
- Upsert or replace department rows inside one controlled transaction.
- Do not duplicate metadata or handoff rows.
- Do not publish another task for a ticket already queued/running/complete.
- If a worker partially finishes and the process crashes, the ticket must not become `intake_complete`.
- Task completion is not authoritative until DB persistence succeeds.
- Celery's expiring result backend is operational evidence only, not the ticket source of truth.

## UI requirements

Add the feature to the existing authenticated backoffice shell, recommended route `/backoffice/rfp` and navigation label such as `RFP intake`.

The UI must support:

1. PDF selection with clear accepted type/size guidance.
2. Upload through the authenticated API helper.
3. Immediate display of the new ticket and `analyzing` state.
4. Polling with cleanup/backoff while the ticket is queued/running/retrying.
5. A ticket list and/or detail view showing safe lifecycle state.
6. Completed metadata and readability metrics.
7. Per-department cards showing department name, named owner, key aspects, and open questions.
8. Fixed safe states for discarded non-RFP, PHI block, queue/processing failure, and inaccessible ticket.
9. A visible statement that the result is intake analysis, not a completed proposal or approval.

Accessibility and safety:

- Use a real label for the file input, keyboard-operable controls, visible focus, semantic status/live-region updates, and sufficient color contrast.
- Do not render raw backend `detail`, stack traces, file paths, PDF text, or model responses.
- Stop polling on terminal business status or terminal operational failure, and cancel timers/requests on unmount.
- Avoid duplicate submissions while an upload is in flight.
- Use the existing `apiClient` error mapping and auth redirect behavior.
- Do not add a raw PDF preview because it may contain PHI.

## Seed PDFs and exact expected outcomes

The supplied curriculum PDFs are validation uploads and also establish the Part 2 seed cases. They must be uploaded through the UI; do not copy them into `data/raw/` as static seeded inventory.

### 1. Meridian Manufacturing - formal RFP - accept

Source: <https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/09-agentic-workflows/rfp-requests/healthcore/healthcore-request-1.pdf>

Expected metadata and routing:

- `client_name`: Meridian Manufacturing, Inc.
- `client_country`: `US` (Austin, Texas)
- program: on-site occupational health plus corporate wellness
- `covered_population`: 800 employees
- proposal deadline: August 23, 2026
- contract term: 12 months with renewal option
- budget: missing/null; Revenue should ask for it
- currency: USD
- departments: `revenue`, `clinical`, `compliance`
- compliance aspect: BAA/HIPAA and data security
- classification: accept even without a reference budget

Expected worker evidence includes:

- Revenue: pricing is 25% of evaluation; electronic submission deadline; 12-month term; budget/payment questions remain open.
- Clinical: on-site clinic three days per week; injury/illness triage; annual screenings for 800 employees; chronic-condition support; staffing/capacity is weighted heavily.
- Compliance: BAA required before contract execution; HIPAA/data-security review.

Do not promote the named Meridian contact into a HealthCore department owner.

### 2. Thames Valley University - informal request - accept

Source: <https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/09-agentic-workflows/rfp-requests/healthcore/healthcore-request-2.pdf>

Expected metadata and routing:

- `client_name`: Thames Valley University
- `client_country`: `UK`
- program: referral network partnership
- `covered_population`: around 3,000 students
- requested delivery: access through a satellite clinic
- requested start: next term, around August 28; this is not automatically a proposal submission deadline
- proposal deadline: missing/null; record an open question
- budget: missing/null
- currency: GBP
- departments: `revenue`, `clinical`, `compliance`
- compliance aspect: DPA and UK GDPR
- classification: accept despite email-like tone, missing budget, and missing formal RFP headings

### 3. MedFlow vendor pitch - reject

Source: <https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/09-agentic-workflows/rfp-requests/healthcore/healthcore-request-3.pdf>

Expected behavior:

- Classify as not an RFP because MedFlow is selling an EHR platform to HealthCore rather than requesting a HealthCore proposal.
- Mark the ticket `discarded` with a safe reason code such as `not_an_rfp`.
- Create no RFP metadata/workstream result beyond safe classifier/audit fields needed for the discarded ticket.
- Run no department workers or synthesizer.
- Do not fail or block other tickets.

### 4. Improper-PHI critical fixture - create synthetically

Create a synthetic test PDF or conversion fixture containing reserved fake markers that represent a patient name/identifier and diagnosis. Never use real PHI. Expected behavior:

- The privacy gate blocks it before any agent call.
- No marker appears in logs, DB fields, API responses, UI, task result, checkpoint, or generated Markdown artifact.
- The ticket records only safe flags/reason codes and the fixed Compliance handling message.
- No metadata/classifier/orchestrator/worker/synthesizer model call occurs.

## Testing requirements

Implementation and validation are one task. Follow existing test patterns and use deterministic fakes; no test should require a live model, Supabase project, Redis service, or external network unless clearly labeled as an optional smoke test.

### Pipeline unit tests under `tests/pipelines/`

At minimum:

- classifier accepts formal Meridian content;
- classifier accepts informal Thames content;
- classifier rejects MedFlow vendor pitch;
- classifier output schema rejects unknown/malformed results;
- at least one worker produces only its allowed structured facts;
- compliance is always selected;
- unknown departments do not create workers;
- missing population/budget/deadline becomes an open question, not an invented value;
- country deterministically maps to USD/GBP and BAA/DPA expectations;
- worker fan-out/fan-in includes all expected results exactly once;
- contradictions remain structured open questions;
- synthesizer rejects missing compliance, duplicates, unknown departments, PHI, and unsupported facts;
- prompt-injection text in a PDF cannot change roles, department ids, or policy;
- empty/short conversion and readability edge cases are controlled;
- PHI fixture causes zero downstream agent calls and zero marker leakage.

### API, persistence, and task tests under `services/api/tests/`

- unauthenticated upload/list/detail is rejected;
- valid PDF upload returns `202` quickly with an analyzing ticket;
- zero-byte, oversized, wrong MIME, bad signature, multiple-file, and traversal-style filenames are rejected safely;
- stored path is opaque and does not use original filename;
- enqueue receives only safe identifiers;
- broker failure leaves no invisible/orphan state;
- GET polling returns state and results correctly;
- discarded reason messages are fixed and sanitized;
- idempotent retry does not duplicate rows;
- `intake_complete` is written only after metadata, all sections, and handoff exist;
- database transaction rollback leaves status truthful;
- cross-user access follows the selected authorization policy;
- exhausted task failure uses safe operational state and does not masquerade as classifier rejection;
- new SQLModel tables work on temporary SQLite and use PostgreSQL-compatible types/constraints.

### UI tests

- upload sends multipart PDF through the authenticated client;
- duplicate submit is prevented;
- analyzing state polls and cleans up timers;
- accepted result renders metadata/readability and all three department owners/workstreams;
- discarded and PHI-blocked states show fixed safe messages;
- API errors never render raw server details;
- file input and status updates are accessible;
- polling stops on completion/discard/failure and on unmount.

### Manual acceptance through the UI

Upload each supplied PDF from the briefing folder and capture safe evidence of:

1. Meridian accepted and routed to all three departments.
2. Thames accepted despite informal format and routed to all three departments.
3. MedFlow discarded without worker execution.
4. Ticket status moving from `analyzing` to the correct terminal state.
5. Stored metadata/readability and department results being visible without reading the PDF.

Evidence must not contain PHI, secrets, tokens, raw prompts, or raw model output. A live-model smoke check is optional and must be reported separately from deterministic test results.

## Acceptance criteria

Part 1 is complete only when all of the following are true:

- The feature extends the existing FastAPI backend and `uis/web`; no second service/app exists.
- The dedicated graph is under `data/pipelines/rfp_intake/` and separate from the existing staff agent.
- Upload returns quickly with `202`; conversion/agents run asynchronously in the existing worker.
- Backend and worker share protected `data/raw/` storage; uploaded filenames are opaque and runtime files are ignored by Git.
- Tickets, RFP metadata, department key aspects, and the handoff are persisted through SQLModel in PostgreSQL/Supabase-compatible tables.
- PDF-to-Markdown conversion occurs before any agent reads content.
- The deterministic privacy gate runs before every agent and the improper-PHI case leaks no marker anywhere.
- Formal and informal institutional requests are accepted; the vendor pitch is rejected.
- Metadata/readability is stored without invented values.
- Orchestrator, department workers, and synthesizer are distinct responsibilities with real fan-out/fan-in.
- Only `revenue`, `clinical`, and mandatory `compliance` workstreams are produced, with the exact named owners.
- Workers receive metadata plus relevant extracts, not unrestricted raw documents.
- The UI lets Revenue Cycle understand what each department needs and whom to ask without reading the original PDF.
- `intake_complete` always has a persisted `ticket_id` plus validated synthesizer/workstream payload ready for Part 2.
- Part 2/3 behavior has not been implemented.
- Focused tests pass and any unverified live-provider/Supabase behavior is stated honestly.

## Implementation sequence for Cursor

1. Re-read `AGENTS.md`, active memory files, `.agents/rules/`, and current relevant code. Do not read archives unless the user asks.
2. Confirm current branch/status and preserve unrelated user changes. Create a branch only if explicitly requested in the build session.
3. Confirm API/worker/UI/database paths and dependency conventions.
4. Write failing focused tests for typed contracts, classifier boundaries, PHI isolation, and ticket transitions.
5. Add SQLModel persistence and transactional repository methods.
6. Add safe upload/file storage and authenticated ticket routes.
7. Add the Celery task and shared Compose raw-data mount.
8. Add conversion, privacy gate, readability, structured classifier, and metadata extraction.
9. Add orchestrator, parallel workers, synthesizer, and transactional completion.
10. Add the `uis/web` upload/poll/result experience.
11. Run narrow tests first, then affected API/UI typecheck/lint/build checks, then manual seed uploads.
12. Update the memory bank with actual implementation decisions and validation. Do not claim checks that were not run.
13. Stop before commit, push, PR, Supabase migration, or deployment unless the user explicitly requests those actions.

## Required implementation handoff

When Cursor finishes the build, it must report:

- files and behavior changed;
- final schema and migration/setup method;
- API endpoints and example safe responses;
- final graph/state flow and model boundaries;
- dependency changes and why they were needed;
- tests added/updated;
- exact validation commands and results;
- manual outcome for each of the three supplied PDFs;
- PHI leakage checks and their results;
- any live model, PostgreSQL/Supabase, Redis, Docker, or UI behavior that remains unverified;
- no commit/push/PR unless separately authorized.
