"""Expiry, duplicate collapse, and a second privacy check before consolidation writes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agent.consolidation import consolidate
from app.agent.memory_store import MemoryStore


def _store(tmp_path) -> MemoryStore:
    return MemoryStore(str(tmp_path / "memory.sqlite"))


def _approve(store: MemoryStore, content: str, category: str, subject: str, now: datetime) -> str:
    created = store.create_proposal(
        owner_user_id="user-1",
        conversation_id="conversation-1",
        run_id="run-1",
        action="add",
        category=category,
        subject_key=subject,
        content=content,
        rationale="later",
        now=now,
    )
    assert created["ok"]
    resolved = store.resolve(
        created["proposal"].proposal_id,
        owner_user_id="user-1",
        conversation_id="conversation-1",
        label="approve",
        now=now,
    )
    assert resolved["saved"]
    return resolved["memory_id"]


def test_category_expiry_hides_the_memory(tmp_path) -> None:
    store = _store(tmp_path)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    _approve(
        store,
        "The referral system tends to fail on Monday mornings because of the overnight batch job.",
        "incident_pattern",
        "monday-batch",
        start,
    )
    later = start + timedelta(days=31)
    assert store.list_active("user-1", later) == []
    assert store.list_memories("user-1")[0].status == "expired"


def test_pending_proposal_expires_without_approval(tmp_path) -> None:
    store = _store(tmp_path)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    created = store.create_proposal(
        owner_user_id="user-1",
        conversation_id="conversation-1",
        run_id="run-1",
        action="add",
        category="presentation_preference",
        subject_key="vacancies",
        content="The signed-in user wants the weekly vacancies report broken down by role.",
        rationale="later",
        now=start,
    )
    assert created["ok"]
    assert store.get_pending("user-1", "conversation-1", start + timedelta(hours=25)) is None
    audit = store.list_audit("user-1")[0]
    assert audit.status == "expired"
    assert store.list_memories("user-1") == []


def test_exact_duplicates_collapse_and_conflicts_stay_separate(tmp_path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 3, 1, tzinfo=timezone.utc)
    shared = "At the Manchester clinic, internal referrals now go through the coordinator."
    store.import_legacy(
        owner_user_id="user-1",
        category="operational_correction",
        subject_key="manchester-a",
        content=shared,
        now=now,
    )
    store.import_legacy(
        owner_user_id="user-1",
        category="operational_correction",
        subject_key="manchester-b",
        content=shared,
        now=now + timedelta(minutes=1),
    )
    store.import_legacy(
        owner_user_id="user-1",
        category="operational_correction",
        subject_key="austin-road",
        content="The high no-show alert at the Austin clinic was caused by a road closure that week.",
        now=now,
    )
    first = consolidate(store, "user-1", now + timedelta(minutes=2))
    assert first["superseded"] == 1
    active = [row.content for row in store.list_memories("user-1") if row.status == "active"]
    assert active.count(shared) == 1
    assert any("road closure" in item for item in active)
    second = consolidate(store, "user-1", now + timedelta(minutes=3))
    assert second == {"quarantined": 0, "superseded": 0}


def test_consolidation_quarantines_phi_and_keeps_ownership(tmp_path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 4, 1, tzinfo=timezone.utc)
    store.import_legacy(
        owner_user_id="user-1",
        category="operational_correction",
        subject_key="bad",
        content="Remember that patient Alex Example cancelled.",
        now=now,
    )
    store.import_legacy(
        owner_user_id="user-2",
        category="operational_correction",
        subject_key="other",
        content="The signed-in user wants the weekly vacancies report broken down by role.",
        now=now,
    )
    result = consolidate(store, "user-1", now)
    assert result["quarantined"] == 1
    hidden = store.list_memories("user-1")[0]
    assert hidden.status == "deleted"
    assert hidden.content == ""
    assert hidden.privacy_reason == "phi_detected"
    assert "Alex Example" not in repr(store.list_memories("user-1"))
    assert store.list_active("user-2", now)[0].owner_user_id == "user-2"


def test_repeated_approval_does_not_create_two_memories(tmp_path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 5, 1, tzinfo=timezone.utc)
    created = store.create_proposal(
        owner_user_id="user-1",
        conversation_id="conversation-1",
        run_id="run-1",
        action="add",
        category="presentation_preference",
        subject_key="vacancies",
        content="The signed-in user wants the weekly vacancies report broken down by role.",
        rationale="later",
        now=now,
    )
    first = store.resolve(
        created["proposal"].proposal_id,
        owner_user_id="user-1",
        conversation_id="conversation-1",
        label="approve",
        now=now,
    )
    second = store.resolve(
        created["proposal"].proposal_id,
        owner_user_id="user-1",
        conversation_id="conversation-1",
        label="approve",
        now=now,
    )
    assert first["memory_id"] == second["memory_id"]
    assert len([row for row in store.list_memories("user-1") if row.status == "active"]) == 1


def test_a_second_pending_proposal_is_refused(tmp_path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 5, 2, tzinfo=timezone.utc)
    first = store.create_proposal(
        owner_user_id="user-1",
        conversation_id="conversation-1",
        run_id="run-1",
        action="add",
        category="operational_correction",
        subject_key="one",
        content="At the Manchester clinic, internal referrals now go through the coordinator.",
        rationale="later",
        now=now,
    )
    second = store.create_proposal(
        owner_user_id="user-1",
        conversation_id="conversation-1",
        run_id="run-2",
        action="add",
        category="operational_correction",
        subject_key="two",
        content="The referral system tends to fail on Monday mornings because of the overnight batch job.",
        rationale="later",
        now=now,
    )
    assert first["ok"]
    assert second["reason"] == "pending_exists"
    assert store.list_audit("user-1")[0].proposal_id == first["proposal"].proposal_id
