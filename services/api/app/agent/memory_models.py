"""Fields shared by the memory store, the policy, and the graph."""

from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = (
    "operational_correction",
    "incident_pattern",
    "presentation_preference",
)
ACTIONS = ("add", "supersede", "forget")
MEMORY_STATUSES = ("active", "superseded", "expired", "deleted")
PROPOSAL_STATUSES = (
    "pending",
    "approved",
    "rejected",
    "edited",
    "discarded_ambiguous",
    "discarded_topic_change",
    "expired",
    "blocked",
)
DECISION_LABELS = ("approve", "reject", "edit", "ambiguous", "topic_change")

# Course defaults. These are not a HealthCore legal retention period.
EXPIRY_DAYS = {
    "incident_pattern": 30,
    "operational_correction": 180,
    "presentation_preference": None,
}
PENDING_HOURS = 24
CONFIDENCE_MIN = 0.7
MEMORY_LIMIT = 5
MAX_MEMORY_CHARS = 1000


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    owner_user_id: str
    scope_type: str
    scope_key: str
    category: str
    subject_key: str
    content: str
    status: str
    source_proposal_id: str
    created_at: str
    updated_at: str
    expires_at: str | None
    supersedes_memory_id: str | None
    provenance: str
    privacy_reason: str


@dataclass(frozen=True)
class ProposalRecord:
    proposal_id: str
    owner_user_id: str
    conversation_id: str
    run_id: str
    action: str
    category: str
    subject_key: str
    content: str
    rationale: str
    status: str
    decision_label: str
    proposed_at: str
    resolved_at: str | None
    memory_id: str | None
    privacy_reason: str
    target_memory_id: str


@dataclass(frozen=True)
class Decision:
    label: str
    confidence: float
    edited_content: str | None = None
    remainder: str | None = None
