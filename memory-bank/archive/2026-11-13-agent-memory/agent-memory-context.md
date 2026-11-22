# HealthCore LangGraph Agent Memory and Self-Improvement Context

## Purpose of This Document

This file is the implementation handoff for the HealthCore **Agent Memory and Self-Improvement** branch. It combines the generic 4Geeks Milestone 8 Part 1 assignment with the HealthCore-specific briefing and the current repository architecture.

Cursor is expected to act as the implementation architect: inspect the current code, make the final low-level design choices, write the implementation plan, implement the feature, test it, document it, and prepare evidence. The requirements and invariants in this document are the contract Cursor must satisfy.

This document does **not** implement the feature. Its creation must not be treated as authorization to create a branch, install dependencies, change application code, commit, push, open a pull request, deploy, or modify production data.

## Source Documents and Authority Order

Use these sources in this order when requirements appear to conflict:

1. The HealthCore briefing, especially its absolute PHI prohibition:
   `https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/08-agent-engineering/memory/healthcore-BRIEFING.md`
2. The generic milestone README and grading rubric:
   `https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-agentic-engineering/README.md`
3. The repository's root `AGENTS.md`, scoped `.agents/rules/`, active memory bank, and current code.
4. Existing repository conventions and tests.

The HealthCore privacy rule is stricter than the generic assignment. Where the generic rubric asks for an originating message to be logged, HealthCore's prohibition on PHI in events, tables, logs, memory, endpoints, and generated output takes precedence. Preserve auditability using safe references and sanitized, validated fields; never preserve prohibited raw content merely to satisfy an audit example.

## Branch and Scope

The milestone expects a new branch named:

```text
feature/agent-memory
```

Create it from the latest approved progress containing the existing LangGraph agent and MCP integration. Do not create a new repository and do not build a replacement agent.

This branch must extend the existing signed-in HealthCore support agent so that it can:

1. use previously approved, applicable memories in later interactions;
2. self-evaluate an interaction for a possible memory;
3. propose a safe candidate to the user in the same conversation;
4. classify the user's explicit response to the pending proposal;
5. write only approved, validated memories;
6. keep an auditable, PHI-safe decision record;
7. consolidate, supersede, expire, or discard memory so it does not grow without control; and
8. preserve the existing RAG-as-a-tool and MCP-tool behavior.

Do not build a new commercial Q&A interface, a multi-agent system, a new knowledge base, a new RAG ingestion workflow, a fine-tuned model, or a knowledge graph unless the final architectural justification demonstrates that one is strictly required. The assignment explicitly expects the same agent with an additional self-evaluation step.

## Current Repository Baseline

Cursor must inspect the current files before designing changes. The important existing implementation is:

- `services/api/app/agent/state.py`
  - `AgentState` currently contains the question, retrieved RAG context, answer, route, incident/tool state, and sources.
- `services/api/app/agent/graph.py`
  - builds the existing LangGraph support-agent graph;
  - validates a question;
  - routes to RAG, incident MCP lookup, or both;
  - generates or joins an answer;
  - currently ends after the answer;
  - invokes the graph with `run_id` as LangGraph `thread_id`.
- `services/api/app/agent/incidents.py`
  - calls the HealthCore MCP server with the authenticated staff bearer token;
  - limits incident output to the existing safe-field contract.
- `services/api/app/agent/trace.py`
  - stores ordered graph events in SQLite;
  - currently stores answer text and other run metadata.
- `services/api/app/routers/agent.py`
  - exposes authenticated `POST /agent/query`;
  - currently accepts only `question` and returns `answer` plus a per-turn `run_id`.
- `services/api/app/main.py`
  - creates the SQLite LangGraph checkpointer and trace store during FastAPI lifespan;
  - compiles the graph once.
- `services/api/tests/test_agent.py`
  - contains the existing signed-in, validation, failure-sanitization, RAG, and MCP incident contracts.
- `services/api/app/auth/security.py`
  - resolves the authenticated user from the bearer token;
  - the router currently uses authentication as a dependency but does not pass a stable user identity into the graph.
- `docs/rag/rag-design.md`
  - defines the read-only `healthcore_knowledge` Qdrant collection and existing privacy/logging constraints;
  - explicitly states that the current RAG feature has no chat memory.
- `mcps/healthcore-company-tools/README.md`
  - documents the authenticated, read-only incident and inventory tools.
- `services/api/pyproject.toml`
  - already includes LangGraph, SQLite checkpointing, Redis, Qdrant, and MCP dependencies.

The current system already has two kinds of persistence that are **not** the new approved-memory store:

- LangGraph checkpoints are execution/conversation state.
- `healthcore_knowledge` is curated company RAG content.

Neither may be relabeled as approved agent memory. The new memory capability needs an explicit interface and a distinct persistence boundary.

## Business Context

HealthCore operates 12 clinics in the United States and the United Kingdom. The agent already knows approved company policy through RAG and can query HealthCore operational tools through MCP. It supports staff with operational questions; it is not a clinical decision-maker and must not become one.

Claire Whitfield, Chief Compliance Officer, requires review of persistent memory and the later Part 2 harness before release. The implementation and evidence must therefore be reviewable, minimal, and explicit about data handling.

The motivating failure is repeated correction: users currently have to re-explain operational facts or presentation preferences because every interaction begins without durable, user-approved memory.

## Required User-Visible Outcome

The completed agent should behave like this:

1. A signed-in staff member asks a normal operational question or provides an operational correction.
2. The agent uses approved RAG and MCP tools as it already does.
3. The agent also retrieves only relevant, active, previously approved agent memories for the authenticated scope.
4. It answers the user's current request.
5. In the same structured generation step, it decides whether the interaction contains a genuinely useful new or corrected non-clinical fact.
6. If there is nothing worth remembering, it ends normally without mentioning memory.
7. If there is a safe candidate, it shows the exact proposed memory and asks whether the user wants it remembered.
8. The proposal remains pending; it is not yet in durable memory.
9. On the user's next message, the system first classifies that message against the one pending proposal as approval, rejection, edit, or no clear decision.
10. An approval writes the validated candidate. An edit validates and writes the edited candidate only if it remains safe. A rejection writes no memory. Ambiguity, silence, or topic change never becomes approval.
11. The system records a PHI-safe audit outcome for the proposal regardless of approval or rejection.
12. Any remaining question in the same user message is handled normally after the pending proposal is resolved.
13. A future relevant interaction can use an approved memory, with source/scope metadata retained internally.

## Non-Negotiable HealthCore Privacy Rule

No patient identifier or PHI under HIPAA or UK GDPR may appear in any of the following:

- an approved memory;
- a pending proposal;
- a rejected proposal's stored payload;
- a consolidation candidate or consolidated record;
- a LangGraph checkpoint;
- a trace event;
- an audit table;
- an application log;
- an API response or error payload;
- generated output;
- a test fixture, snapshot, example, screenshot, or evidence artifact;
- a vector-store payload, embedding input, cache entry, queue message, or telemetry event.

Forbidden content includes, at minimum:

- patient names;
- medical record numbers;
- dates of birth;
- diagnoses;
- insurance numbers;
- clinical notes;
- lab results;
- medical-visit content;
- any combination of otherwise ordinary fields that could re-identify a patient.

Do not interpret user consent as permission to store PHI. A user cannot override this rule by asking, approving, editing, or insisting.

The agent must explicitly refuse a request to remember patient or clinical content, explain the restriction without echoing the prohibited details, and avoid creating a pending proposal. It must not silently ignore the request.

### Required Privacy Gates

Use a centralized, reusable validation boundary. Validation must occur at all of these points:

1. **Before checkpointing or tracing user content.** Raw input must not leak into persistent execution state or logs.
2. **Before a proposal is shown.** A model-produced candidate cannot be trusted merely because the model labeled it safe.
3. **After a user edits a proposal.** The edited candidate is new untrusted input.
4. **Immediately before any memory write.** This is a final fail-closed guard against bypass or race conditions.
5. **Before approved memories are inserted into a model prompt.** Revalidate legacy or migrated rows.
6. **Before consolidation, summarization, deduplication, or supersession writes.** The briefing explicitly requires this second validation.
7. **Before trace, audit, log, API, or evidence serialization.** Safe fields must be allow-listed.

The validator should return a structured result such as `allowed`, `reason_codes`, and a safe replacement/handling instruction. It must fail closed on errors or low confidence.

Do not rely exclusively on an LLM saying that text is PHI-free. Use deterministic rules for known identifier formats and explicit sensitive categories, then add contextual/semantic classification as needed. Document known limits and test both false negatives and important false positives, including the distinction between a confirmed staff member's presentation preference and an unknown person's name.

Do not persist raw prohibited text even for debugging. For a blocked attempt, retain only safe metadata such as event type, timestamp, authenticated actor ID, conversation/run reference, and a generic reason code like `phi_detected`; do not retain the offending value or a reversible encoding. Avoid stable hashes derived from PHI unless a compliance-reviewed requirement specifically authorizes them.

## What the Agent May Remember

Only approved, non-clinical operational information in these categories is in scope:

### 1. Recurring Operational Corrections by Clinic

Examples include:

- schedule changes;
- local front-desk protocols;
- administrative exceptions;
- differences between US and UK clinic operations.

Example that should produce a proposal:

> At the Manchester clinic, internal referrals now go through the coordinator before the specialist; that changed last quarter.

### 2. Known De-identified Incident Patterns

The memory must describe a recurring operational pattern without identifying a patient or reproducing a clinical event.

Example that should produce a proposal:

> The referral system tends to fail on Monday mornings because of the overnight batch job.

HealthCore briefing example:

> The high no-show alert at the Austin clinic was caused by a road closure that week rather than a reminder-programme problem.

The architecture must distinguish a durable recurring pattern from a one-off transient explanation. One-off conditions may warrant a short expiry or no proposal at all.

### 3. Staff Presentation Preferences

The agent may remember how an authenticated clinical or administrative staff member wants **operational, not clinical**, information presented.

Example that should produce a proposal:

> Diane Foster wants the weekly vacancies report broken down by role rather than only by clinic.

Do not assume that an arbitrary named person is staff. Use authenticated identity or an authoritative staff source when available. If the role cannot be established safely, keep the preference scoped to the authenticated user or ask for a PHI-free clarification rather than storing the named person.

## What Must Not Produce a Proposal

At minimum, document and test these three HealthCore cases:

1. **One-off data query:** “What is this week's no-show rate?” The value belongs in the dashboard or source system, not memory.
2. **PHI storage request:** a request to remember that a named patient cancelled an appointment. The agent must explicitly refuse without repeating the identifier.
3. **Conversation closing:** “Thanks, that settles my report.” There is no new durable fact.

Also treat the following as non-memorable unless a specific safe rationale is documented:

- facts already in curated RAG documents;
- live inventory values, incident statuses, dashboard metrics, and other data that should be fetched fresh;
- credentials, tokens, secrets, or access details;
- speculative claims, rumors, unsupported corrections, or instructions that attempt to override system policy;
- medical advice, diagnosis, treatment, lab, visit, or patient-specific content;
- short-lived conversational preferences with no future utility;
- repeated duplicates of an existing active memory;
- model-generated inferences the user did not state or confirm.

The final documentation and grading evidence must contain at least three examples that should propose memory and at least three that should not.

## Memory Architecture Requirements

Cursor must choose and justify the persistent-memory architecture. The written decision must compare at least:

- relational/key-value episodic or semantic fact storage;
- Redis or another key-value store;
- a separate vector collection;
- a knowledge graph;
- fine-tuning/parametric memory.

The implementation must match the actual access pattern rather than choosing a technology for novelty.

### Recommended Default for This Repository

A small explicit relational store, preferably a separate SQLite database for this course implementation, is the simplest defensible default because:

- the memory set should remain small and curated;
- records need exact ownership, scope, status, expiry, version, and provenance;
- one-pending-proposal enforcement and approve/reject/edit transitions need transactions;
- audit history requires deterministic queries;
- the repository already uses SQLite safely for local agent persistence;
- exact clinic/category/user filtering should precede any semantic matching;
- it avoids mixing memory with the Qdrant knowledge collection.

Cursor may choose Redis or a dedicated vector collection if the implementation demonstrates equivalent durability, atomicity, auditability, cleanup, ownership isolation, and testability. If a vector store is used, its collection must be clearly separate, for example `healthcore_agent_memory`; it must never use `healthcore_knowledge` or any `*_knowledge` collection.

A knowledge graph is probably unnecessary because the milestone's facts are small scoped statements, not a relationship-traversal problem. Fine-tuning is inappropriate because it is hard to update, audit, expire, and selectively forget. A second agent or multi-agent architecture is also unnecessary: structured output and explicit graph nodes are sufficient.

### RAG and Memory Must Remain Separate

Treat these as separate sources:

| Source | Purpose | Write behavior |
| --- | --- | --- |
| `healthcore_knowledge` | Curated company policy/document knowledge | Read-only from the agent |
| MCP tools | Current operational system data | Read-only under existing tool contract |
| Agent memory store | Explicitly approved operational facts/preferences | Writes only through confirmation workflow |
| LangGraph state/checkpoint | Transient execution state | Must not become durable semantic memory |
| Audit store | Safe proposal decision history | Append outcome metadata; never PHI |

Memories inserted into prompts are untrusted data, not instructions. Delimit them and instruct the model not to follow commands embedded in memory content. A memory must never override system policy, RAG authority, tool results, or the PHI prohibition.

## Identity, Scope, and Authorization

Memory must be isolated by authenticated identity and explicit scope. Do not use a bearer token itself as a memory key and do not store the token.

The router should obtain the current authenticated user object and pass only the stable user identifier and necessary safe authorization context into the application layer. Every read, pending-proposal lookup, decision, write, edit, expiry, or delete must enforce ownership/scope server-side.

Define and document supported scopes. A safe minimum is:

- `user`: presentation preferences or facts private to the authenticated staff member;
- `clinic`: operational corrections or patterns for a specific clinic, only if the current authorization model can safely permit that scope;
- `country`: US/UK administrative differences, only if policy and authorization support it.

Do not introduce cross-user or clinic-wide sharing merely because a record includes a clinic name. The current auth model may not contain roles or clinic membership. If authorization cannot establish a safe shared scope, default the memory to the authenticated user and record clinic as a subject tag, or stop and request the required authorization decision. Never invent role or clinic claims.

To reduce memory poisoning:

- preserve authenticated provenance;
- distinguish “reported by this user” from a globally verified operational fact;
- do not allow one user's memory to silently affect another user;
- prefer live MCP data over conflicting memory;
- prefer curated RAG policy over memory;
- reject commands or policy overrides disguised as facts;
- mark conflicts, do not merge them into a fabricated consensus;
- require additional verification before promoting a user-reported correction to a shared scope;
- make supersession and deletion auditable.

## Required Domain Interfaces

Implement explicit interfaces rather than spreading SQL/Redis/Qdrant calls across graph nodes. Exact names may follow repository conventions, but responsibilities should include:

### Memory Repository

- retrieve applicable active memories by authenticated owner/scope, clinic/country/category, and query;
- create a memory from an approved proposal;
- supersede or update an existing memory without destroying history;
- mark a memory expired or deleted;
- deduplicate exact and near-equivalent memories;
- list records eligible for cleanup or consolidation;
- enforce all ownership and status filters internally.

### Proposal/Audit Repository

- create at most one pending proposal for a conversation/owner;
- fetch the pending proposal atomically;
- transition it exactly once to approved, rejected, edited, discarded, expired, or blocked;
- record timestamps, safe provenance, decision label, and resulting memory reference;
- prevent double approval under retries or concurrent requests;
- retain rejected outcomes without retaining prohibited raw content.

### Privacy Validator

- validate candidate memory content;
- validate user-edited content;
- validate content immediately before persistence;
- validate recalled and consolidated content;
- provide generic safe reason codes;
- never log the rejected text.

### Consolidation Service

- find duplicate, superseded, stale, or low-value records;
- apply category-specific expiry and consolidation policy;
- revalidate the output for PHI before writing;
- keep provenance from all source memories;
- produce an auditable result;
- be deterministic and testable without live model calls where practical.

## Suggested Persistent Data Contract

Cursor may refine field names, but the final schema must preserve these semantics.

### Approved Memory Record

- `memory_id`: opaque random identifier;
- `owner_user_id`: stable authenticated user identifier;
- `scope_type`: `user`, `clinic`, or another explicitly approved scope;
- `scope_key`: safe identifier for that scope;
- `category`: operational correction, incident pattern, or presentation preference;
- `subject_key`: normalized safe subject used for deduplication;
- `content`: exact PHI-validated statement the user approved;
- `status`: active, superseded, expired, or deleted;
- `source_proposal_id`: immutable link to the authorizing proposal;
- `created_at`, `updated_at`, and optional `expires_at` in UTC;
- `supersedes_memory_id` or version lineage where applicable;
- `last_used_at` and/or use count only if needed for cleanup, without storing prompts;
- safe provenance indicating user-approved versus separately verified.

### Proposal and Decision Audit Record

- `proposal_id`: opaque random identifier;
- `owner_user_id` and conversation reference;
- origin `run_id`/turn reference, not a raw PHI-bearing message;
- proposed action: add, update, supersede, or forget;
- category, scope, subject, and candidate content only after PHI validation;
- safe rationale for why it may be useful;
- status: pending, approved, rejected, edited, discarded ambiguous, discarded topic change, expired, or blocked by privacy;
- structured decision label and optional confidence;
- `proposed_at` and `resolved_at` in UTC;
- resulting `memory_id` when a write occurs;
- generic privacy reason code when blocked, with no offending text.

If the originating input is guaranteed PHI-free by an earlier non-persistent validation gate, the audit may store a minimal sanitized summary. Otherwise retain only safe event/run references. Document this deliberate HealthCore adaptation of the generic “originating message” audit requirement.

### Database Constraints

Enforce invariants in storage, not just in prompts:

- one unresolved proposal per authenticated owner/conversation;
- a proposal can transition from pending only once;
- an approved write must reference its proposal;
- no active exact duplicate for the same owner/scope/category/subject;
- timestamps are UTC;
- status/category/scope use constrained values;
- retrying the same request is idempotent.

## LangGraph Flow Requirements

Extend the existing graph rather than replacing its RAG/MCP routes. The final graph should make these responsibilities visible and testable as nodes or clearly separated services.

### Turn Start

1. Resolve the authenticated actor and conversation ID outside untrusted model control.
2. Check for one pending proposal for that actor/conversation.
3. If one exists, classify the new user message against that proposal before normal question routing.

### Pending Decision Classification

Use structured output with an enum, not substring logic such as checking whether `"yes"` occurs. The classification should express at least:

- `approve`;
- `reject`;
- `edit`;
- `ambiguous`;
- `topic_change` or equivalent no-decision state.

For `edit`, return the exact edited candidate and any remaining user request separately. For messages such as “Yes, save it, and what is today's inventory status?”, return both the approval and the continuation question.

Use a documented confidence policy. If a decision cannot be determined with reasonable confidence, do not approve. Close/discard the pending proposal by default as required by the milestone, or use a short explicit expiry policy if the rubric permits it; the chosen behavior must be deterministic and documented. Silence, timeout, navigation away, or a new topic must never become approval.

### Resolve Before Continuing

1. Approve: revalidate candidate, transactionally write memory and close proposal.
2. Reject: close proposal; write no memory.
3. Edit: validate the edited candidate; if safe, write exactly the edited content and close the proposal. If unsafe, refuse and close without a memory write.
4. Ambiguous/topic change: discard or reject by default; write no memory.
5. Continue with any residual normal question in the same turn.

### Memory Read

Before answer generation, retrieve only memories that are:

- owned by or safely visible to the authenticated actor;
- active and unexpired;
- applicable to the current clinic/country/category/query;
- still PHI-safe on read;
- within a documented result and token limit.

If memory retrieval fails, the agent should continue with existing RAG/MCP behavior where safe and clearly avoid claiming it remembered something. Do not turn a memory backend outage into fabricated recall.

### Existing RAG/MCP Answer Path

Preserve existing behavior:

- validate the question;
- route to RAG, MCP incident lookup, or both;
- keep MCP authentication server-controlled;
- prefer live incident/inventory data over memory;
- preserve honest no-context and sanitized service-unavailable responses.

Memory is extra context, not a replacement for retrieval or tools.

### Self-Evaluation

After or as part of generating the user-facing answer, obtain structured output containing:

- `response_text`;
- `memory_proposal` as a nullable object;
- when present: operation, category, scope, subject, exact candidate content, and safe rationale.

The simplest acceptable design is a single structured model call that generates both the answer and proposal candidate. A separate agent is not needed. A second deterministic validation call/service is still required before display or persistence if needed for safety.

The model must be able to return `memory_proposal: null` for most turns. “Always propose” fails the assignment.

### Proposal Display

Only after the privacy gate passes:

- show the exact candidate memory;
- explain briefly why it could help later;
- ask for explicit approval, rejection, or an edit;
- identify that nothing has been saved yet;
- store one pending proposal.

If validation fails, do not display the candidate or echo the unsafe details. Provide a generic HealthCore privacy explanation.

## Conversation and HTTP Contract

The current API creates a new `run_id` per request, which is insufficient for a multi-turn pending proposal. Add a separate conversation identifier while preserving a per-turn run identifier.

A reasonable contract is:

```json
{
  "question": "...",
  "conversation_id": "optional existing opaque id"
}
```

and:

```json
{
  "answer": "...",
  "run_id": "per-turn id",
  "conversation_id": "stable conversation id",
  "memory_proposal": {
    "proposal_id": "opaque id",
    "content": "exact safe candidate",
    "status": "pending"
  }
}
```

The exact response shape may vary, but it must support:

- a stable conversation across turns;
- one pending proposal;
- clear display of the safe proposed content;
- backwards-compatible handling or coordinated client/test updates;
- server-side ownership checks for any supplied conversation ID;
- opaque, non-enumerable identifiers;
- no client-controlled owner, scope authorization, model, collection, system prompt, or approval status.

Do not use `run_id` as both the turn ID and the durable conversation ID without documenting how separate turns are represented and secured.

## Checkpoints, Traces, Logs, and the Existing Privacy Gap

The current graph state includes raw `question` and `answer`, and the SQLite trace currently stores answer text. A persistent LangGraph checkpointer may therefore serialize user text at every graph step. This is incompatible with the HealthCore rule if a user submits PHI.

Cursor must explicitly inspect and resolve this before claiming compliance. Acceptable strategies include:

- remove persistent checkpointing for raw-content channels and keep safe pending state in the explicit proposal store;
- use transient/non-persisted graph state for raw text;
- sanitize before any checkpoint and prove no earlier checkpoint occurs;
- implement a purpose-built safe checkpoint serializer/store that excludes prohibited fields.

Do not simply reuse a conversation ID as the current SQLite `thread_id`; that can make the privacy problem larger by retaining raw messages across turns.

Traces and application logs should contain only allow-listed operational metadata such as:

- random run/conversation/proposal IDs;
- node name;
- safe status/outcome codes;
- duration;
- counts;
- safe source names;
- memory category and transition status.

Do not log questions, prompts, model output, answers, proposal text, edited text, tokens, clinical content, or raw exception messages. Existing trace behavior that stores `answer` must be changed or justified with an equally strong PHI-proof boundary. Migration/cleanup of pre-existing local trace/checkpoint files must be documented; do not silently delete user data.

## Cleanup and Consolidation Policy

Memory cannot grow forever. Implement and document a functional cleanup mechanism, not only a future recommendation.

Use category-aware policy rather than one arbitrary TTL for everything. A defensible starting point is:

- staff presentation preferences: retain while active; supersede when the user approves a change; optionally require periodic review;
- clinic protocol/schedule corrections: expire or require review after a documented operational interval unless reaffirmed;
- transient incident explanations such as a road closure: short expiry or no memory proposal;
- duplicate facts: consolidate or keep only the newest active version while retaining provenance/audit history;
- rejected/ambiguous proposals: retain only PHI-safe audit metadata according to a documented audit-retention period;
- pending proposals: expire promptly and resolve as not approved.

The exact intervals are an architecture decision and must be justified. Do not invent a HealthCore legal retention period. Label course-project defaults as technical policy pending Compliance approval.

Consolidation must:

1. select eligible records deterministically;
2. preserve owner and scope boundaries;
3. avoid combining conflicting facts into one claim;
4. preserve source proposal/memory lineage;
5. re-run PHI validation on the consolidated output;
6. write the replacement and supersede inputs atomically;
7. leave auditable safe metadata;
8. be idempotent under retries.

Provide an explicit user-initiated “forget” or delete/supersede path if it fits the existing API, or document how selective forgetting occurs through the write interface. Deletion should normally be a status/tombstone transition where audit requirements apply, not silent loss of authorization history.

## Concurrency, Retry, and Failure Behavior

Cover these cases explicitly:

- two requests arrive for the same conversation while a proposal is pending;
- approval is retried after a timeout;
- the same approval is submitted twice;
- a proposal expires between classification and write;
- a user edits a proposal into PHI;
- the memory backend fails after the proposal decision is classified;
- the audit write succeeds but the memory write fails, or vice versa;
- the model returns malformed structured output;
- the privacy validator fails or times out;
- consolidation is run twice;
- an existing memory conflicts with a newly approved correction.

Use transactions/atomic operations where supported. Approval must not produce duplicate memories. On uncertain write outcome, report a safe generic failure and do not claim the memory was saved until the system can confirm it. Privacy validation failure must always fail closed.

## Suggested File Placement

Follow repository conventions and keep backend work under `services/`. Cursor should adapt names to the final architecture, but a likely layout is:

```text
services/api/app/agent/
├── graph.py                 # extend existing flow
├── state.py                 # safe graph state/schema changes
├── memory_models.py         # memory/proposal domain models
├── memory_store.py          # explicit read/write and audit repository
├── memory_policy.py         # memorable criteria, expiry, precedence
├── privacy.py               # centralized PHI validation boundary
├── consolidation.py         # cleanup/consolidation service
└── trace.py                 # PHI-safe metadata-only tracing

services/api/app/routers/
└── agent.py                 # conversation-aware API contract

services/api/tests/
├── test_agent.py
├── test_agent_memory.py
├── test_memory_privacy.py
└── test_memory_consolidation.py

docs/agent/
├── memory-design.md
└── memory-evidence.md
```

Do not create a second API root or a second agent folder merely for the memory milestone. Update `.env.example` only for real, non-secret configuration. Never add actual tokens, patient data, credentials, or production endpoints.

If a new Python dependency is genuinely required, add it with `uv add` from the appropriate project directory and commit the corresponding `pyproject.toml` and `uv.lock` changes. Never use `pip install` or Pipenv for project dependency management.

## Implementation Sequence for Cursor

Before coding:

1. Read root `AGENTS.md`, active memory-bank files, relevant `.agents/rules/`, this context, current agent code/tests, RAG design, MCP README, and auth model.
2. Confirm the baseline tests and repository status without discarding user changes.
3. Write a concrete implementation plan with a file-by-file change map.
4. Record the chosen memory backend, scope model, safe checkpoint strategy, and retention defaults as decisions.
5. Identify any decision that requires HealthCore/Compliance input rather than inventing it.

Then implement in vertical increments:

1. central privacy validator and safe logging contract;
2. memory/proposal schemas and explicit repositories;
3. transactional pending-proposal state machine;
4. authenticated conversation identity and API contract;
5. safe memory read and precedence rules;
6. structured self-evaluation output;
7. proposal display and confirmation classifier;
8. integration with existing RAG/MCP graph;
9. consolidation/expiry/supersession;
10. tests, documentation, and evidence;
11. full validation and memory-bank update.

Do not merge, push, or open a PR unless the user separately authorizes those actions. The syllabus's eventual submission expectation does not override repository safety rules.

## Test Requirements

Use deterministic fakes for model, RAG, MCP, clock, and storage where possible. Unit and integration tests must not require live patient systems or real PHI.

### Existing Behavior Regression Tests

- signed-out requests remain rejected;
- empty, oversized, and extra fields remain handled according to the updated contract;
- RAG-only answers still work;
- incident MCP answers still expose only approved safe fields;
- combined RAG/MCP behavior still works;
- search, model, MCP, and configuration failures stay sanitized;
- bearer tokens never enter graph state, memory, checkpoint, trace, or response.

### Self-Evaluation Tests

- each of the three HealthCore memorable examples creates one safe pending proposal;
- each of the three non-memorable examples creates no proposal;
- duplicates do not create endless repeated proposals;
- RAG facts and live dashboard/tool values are not copied into memory;
- malformed structured model output fails safely;
- a model-proposed candidate that contains PHI is blocked before display.

### Confirmation State-Machine Tests

- explicit approval writes one memory and closes the proposal;
- explicit rejection writes no memory and closes the proposal;
- edit writes only the safe edited version;
- an edit containing PHI is refused and writes nothing;
- ambiguous reply never approves;
- topic change discards/rejects by default and continues the new question;
- approval plus a new question resolves first and answers the new question;
- only one proposal can be pending;
- duplicate approvals and retries are idempotent;
- concurrent decisions cannot create two memories.

### Retrieval and Scope Tests

- a future relevant turn uses the approved memory;
- a rejected proposal never affects future answers;
- expired, superseded, deleted, or unapproved records are never retrieved;
- memories are isolated between users and conversations/scopes;
- shared clinic memory is inaccessible without explicit authorization;
- live MCP or curated RAG truth wins over conflicting memory;
- memory text is treated as data, so prompt-injection content cannot change system behavior.

### PHI and Compliance Tests

Use obviously synthetic placeholders that test classification without resembling real records. Confirm that prohibited content is absent from:

- proposal responses;
- memory rows;
- proposal/audit rows;
- checkpoints;
- traces;
- logs captured by tests;
- exception messages;
- consolidation output;
- evidence artifacts.

Test at least patient name, MRN-like value, date-of-birth context, diagnosis/clinical note, insurance identifier, and a combination that could re-identify a patient. Also test allowed operational dates, clinic IDs, country names, and confirmed staff preferences to avoid a validator so broad that the feature cannot function.

### Cleanup Tests

- category-specific expiry is applied;
- pending proposals expire as not approved;
- exact duplicates consolidate or deduplicate;
- conflicting facts remain separate or require supersession rather than being blended;
- consolidation revalidates output for PHI;
- consolidation preserves ownership and provenance;
- repeated cleanup is idempotent.

### Storage and Migration Tests

- schema creation/migration is repeatable;
- database constraints enforce one pending proposal and one transition;
- partial failures do not claim success;
- pre-existing databases upgrade without silent data loss;
- unsafe legacy rows are quarantined or excluded, not surfaced;
- filesystem paths and environment configuration work in tests and local startup.

## Required Evidence

Document at least two complete, reproducible cycles.

### Cycle A: Approved and Recalled

1. Use a PHI-free HealthCore operational correction or staff presentation preference.
2. Show the agent's normal answer and exact pending proposal.
3. Show explicit approval.
4. Show the safe audit transition and approved memory record without secrets or sensitive content.
5. Start a later relevant interaction.
6. Show that the agent uses the approved memory appropriately.

### Cycle B: Rejected and Unchanged

1. Use a different PHI-free candidate.
2. Show the pending proposal.
3. Show explicit rejection.
4. Show the safe audit transition.
5. Show that no memory record was added or changed.
6. Show a later interaction that does not act as if the rejected candidate were remembered.

Also document a PHI-blocked case, even though the rubric's two required cycles are approval and rejection. The PHI example must not reproduce a patient identifier in screenshots, logs, or committed evidence; use a generic description of the blocked test and safe reason code.

## Required Design Documentation

The implementation documentation and eventual PR description must answer:

1. Which memory type/backend was chosen, and why is it appropriate for HealthCore?
2. Why were Redis-only, vector-only, knowledge graph, and fine-tuning alternatives accepted or rejected?
3. How are RAG knowledge and agent memory physically and logically separated?
4. How does the system decide what is memorable and what is not?
5. How are HIPAA and UK GDPR restrictions both enforced?
6. How is PHI kept out of proposals, writes, checkpoints, traces, logs, outputs, and consolidation?
7. How are approval, rejection, edits, ambiguity, silence, and topic changes classified?
8. How is one pending proposal enforced?
9. How are auditability and HealthCore data minimization reconciled?
10. How are memory ownership, clinic scope, and cross-user isolation enforced?
11. How is poisoning or false correction risk reduced?
12. How does precedence work when memory conflicts with RAG or MCP data?
13. What expires, what is superseded, what is consolidated, and why?
14. Why does this not require a multi-agent architecture?
15. What remains a course-project simplification requiring Claire Whitfield/Compliance review?

Include the production-governance disclaimer: in a real HealthCore environment, core/shared memory changes would go through modification-request tickets and a dedicated review chain. This milestone intentionally simplifies governance to proposal → user confirmation → write/consolidate, but the simplification does not weaken the PHI prohibition.

## Acceptance Criteria

The branch is complete only when all of the following are true:

- [ ] The existing LangGraph/MCP agent is extended rather than replaced.
- [ ] The memory architecture is justified and matches the implemented behavior.
- [ ] The memory store is separate from `healthcore_knowledge` and all `*_knowledge` collections.
- [ ] Explicit read/write interfaces exist; memory is not an ever-growing system prompt.
- [ ] Authenticated identity and memory scope are enforced server-side.
- [ ] The agent distinguishes memorable from non-memorable interactions.
- [ ] At least three examples of each category are documented and tested.
- [ ] A safe proposal is shown in the same conversation and is not written immediately.
- [ ] PHI validation occurs before proposal display.
- [ ] The next message is explicitly classified against the pending proposal.
- [ ] Approval, rejection, edit, ambiguity, topic change, and continuation are deterministic.
- [ ] Silence or ambiguity never becomes approval.
- [ ] Only one proposal can be pending for a conversation/owner.
- [ ] Every safe proposal outcome is auditable without storing PHI.
- [ ] Approved memory can affect a later relevant interaction.
- [ ] Rejected memory never affects later interactions.
- [ ] The implementation has functional cleanup/consolidation with a documented policy.
- [ ] Consolidation revalidates PHI before writing.
- [ ] Memory, proposal, audit, checkpoint, trace, log, endpoint, and evidence paths are PHI-safe.
- [ ] Existing RAG and MCP contracts still pass regression tests.
- [ ] Failure, retry, concurrency, and idempotency cases are tested proportionally.
- [ ] Two complete evidence cycles are documented: one approved, one rejected.
- [ ] The design addresses memory poisoning, conflicts, authority, and selective forgetting.
- [ ] No secrets, real patient data, or fabricated compliance approvals are committed.
- [ ] Dependencies, if any, were added with `uv add` and locks were updated.
- [ ] Relevant tests, lint/type checks, startup checks, and documentation validation actually ran and results were recorded.
- [ ] Claire Whitfield/Compliance review remains an explicit pre-release gate.

## Stop Conditions and Questions Cursor Must Not Guess

Stop and request direction rather than inventing an answer if implementation requires:

- a legal retention period represented as an official HealthCore policy;
- a production authorization model for clinic-wide or country-wide memory;
- access to real patient or clinical data;
- actual production credentials or infrastructure;
- a change to the read-only MCP contract;
- destructive deletion of existing checkpoint/trace databases;
- a migration that could expose or lose unknown user data;
- a new external service with cost or operational commitment;
- a claim that Compliance approved the design.

Course-project defaults may be chosen for local storage paths, TTLs, confidence thresholds, and cleanup schedules only when they are clearly documented as technical assumptions pending review.

## Final Delivery Expectations

Before handing the branch back:

1. verify every acceptance criterion against actual code and tests;
2. run the narrowest tests first, then the applicable full API suite and repository checks;
3. record exact commands and results;
4. document unverified live-service behavior separately from tested behavior;
5. update active memory-bank files with status, decisions, validation, and next step;
6. prepare the architecture rationale and evidence for the eventual PR;
7. do not claim completion for any check that was not run;
8. do not commit, push, open a PR, merge, or deploy without explicit user authorization.

