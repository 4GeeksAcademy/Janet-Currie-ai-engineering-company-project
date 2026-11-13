"""Collapse exact duplicates and drop memories that fail a second privacy check.

Conflicting sentences stay separate. This function does not call a model.
"""

from __future__ import annotations

from datetime import datetime

from app.agent.memory_policy import normalize_fact
from app.agent.memory_store import MemoryStore, utcnow
from app.agent.privacy import is_phi_block, validate_memory_text


def consolidate(store: MemoryStore, owner_user_id: str, now: datetime | None = None) -> dict:
    moment = now or utcnow()
    store._expire_memories(owner_user_id, moment)
    records = [row for row in store.list_memories(owner_user_id) if row.status == "active"]
    quarantined = 0
    superseded = 0
    groups: dict[str, list] = {}
    for record in records:
        checked = validate_memory_text(record.content)
        if is_phi_block(checked) or not checked.allowed:
            store._quarantine(record.memory_id, owner_user_id, moment)
            quarantined += 1
            continue
        groups.setdefault(normalize_fact(record.content), []).append(record)
    for group in groups.values():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda item: item.created_at)
        for older in ordered[:-1]:
            if store.supersede_duplicate(older.memory_id, owner_user_id, now):
                superseded += 1
    return {"quarantined": quarantined, "superseded": superseded}
