# Agent memory design

This is the course implementation of confirm-before-save memory for the existing HealthCore support agent. Claire Whitfield has not approved it. The lifetimes below are technical defaults, not a HealthCore legal retention policy.

In a production HealthCore environment, a change to shared memory would go through a modification-request ticket and a review chain. This milestone uses a smaller loop: propose, user confirmation, then write or consolidate. That smaller loop does not weaken the rule against patient or clinical content.

## 1. Which store, and why

Approved memories and proposal decisions live in one SQLite file, `services/api/data/agent_memory.sqlite` (`AGENT_MEMORY_PATH`). The standard-library driver is the same approach as the agent trace. Records are few, need an owner, a status, an expiry, and a single pending proposal, and those rules belong in the database.

## 2. Alternatives that were not used

Redis is the reporting queue. It does not give this app a durable approve/reject transaction. A vector collection would search before the owner and status filters, and it would sit too close to `healthcore_knowledge`. A knowledge graph is more structure than these short statements need. Fine-tuning cannot expire or revoke one fact. None of those are implemented.

## 3. How policy knowledge stays separate

`healthcore_knowledge` remains the curated policy collection. The agent only reads it. The memory file is a different database. LangGraph checkpoints are per-turn execution state. The audit rows are proposal outcomes, not policy documents.

## 4. What is memorable

Three categories can be proposed: an operational correction, a de-identified incident pattern, and a presentation preference for the signed-in user. One-off metrics, closings, secrets, duplicates, live incident or stock values, and text already contained in a retrieved policy passage are dropped. The model may suggest a candidate. `should_propose` still has to agree, and most turns produce no proposal.

## 5. HIPAA and UK GDPR

The same gate covers both. Patient identifiers, record numbers, dates of birth, clinical wording, insurance identifiers, and combinations that could re-identify a person are refused. A staff member cannot approve an exception. The signed-in user id is the only owner. No clinic-wide or country-wide scope was added, because this auth model has roles and no clinic membership.

## 6. Where text is kept out

The privacy gate runs before a proposal is shown, after an edit, again before the write, again before recalled text is placed in a prompt, and again before consolidation writes. A blocked attempt stores `phi_detected` and empty content. The durable checkpoint keeps status, route, tool outcome, incident id, and source-document names. New trace rows store an empty answer. Questions are not traced. Logs record reason codes, not the submitted sentence.

## 7. How a reply is classified

The reply is one of `approve`, `reject`, `edit`, `ambiguous`, or `topic_change`. Confidence below 0.7 becomes ambiguous. Without a configured model, only a leading phrase such as "Yes, save it" approves. A bare "yes" does not. Ambiguity and a topic change close the proposal and write nothing.

## 8. One pending proposal

SQLite allows one `pending` row per owner and conversation. A second insert fails. A pending row can leave `pending` once. Repeating the same approval returns the memory already written.

## 9. Audit and data minimization

The proposal row keeps the safe sentence the user was shown, the decision, the time, and the memory id when a write happened. It does not keep the bearer token or a blocked sentence. The generic milestone's "originating message" is replaced by the run id and conversation id.

## 10. Ownership

Every read and write filters on `str(user["id"])` from the staff token. The token itself is not stored. A conversation id belongs to the user who first used it. Another user receives "not found".

## 11. Poisoning and false corrections

Memories are user-approved and labeled `user_approved`, not globally verified. One user's row is invisible to another user. Commands inside a memory are data. A memory does not override a policy passage or a live incident result.

## 12. Precedence

The writing prompt says reference passages and live tool results outrank the notes. An incident-only answer is still built from the tool door, not from memory.

## 13. Expiry, supersession, and consolidation

Pending proposals expire after 24 hours as not approved. Incident patterns expire after 30 days. Operational corrections expire after 180 days. A presentation preference stays until the same user approves a replacement for that subject. Exact duplicate text collapses to the newest row. Different sentences are not blended. Forgetting is an approved `forget` proposal, which marks the memory deleted and keeps the audit row. Consolidation is an in-process function, not a Celery job.

## 14. Why this is not a second agent

The existing graph gained `resolve`, `recall`, and `evaluate`. Classification and the privacy gate are ordinary functions. No new agent and no new HTTP service were added.

## 15. What Compliance still has to review

The lifetimes, the decision to keep memory private to one user, and the decision not to build a review ticket queue are course choices. They are not a statement that HealthCore Compliance has accepted them.
