"""SQLite store for approved memories and proposal decisions.

The staff token is never a key. Reads and writes filter by the authenticated user id.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.agent.memory_models import (
    ACTIONS,
    CATEGORIES,
    EXPIRY_DAYS,
    PENDING_HOURS,
    MemoryRecord,
    ProposalRecord,
)
from app.agent.privacy import is_phi_block, validate_memory_text

SAVED_NOTE = "Saved. I will use that on a later question."
EDITED_NOTE = "Saved the edited wording. I will use that on a later question."
REJECTED_NOTE = "I will not remember that."
DISCARD_NOTE = "I did not save that."
FORGOT_NOTE = "I have forgotten that."
UNSAVED_NOTE = "I could not save that. Nothing was stored."


def memory_path() -> str:
    default_dir = Path(__file__).resolve().parents[2] / "data"
    data_dir = Path(os.environ.get("AGENT_DATA_DIR", default_dir))
    path = os.environ.get("AGENT_MEMORY_PATH", str(data_dir / "agent_memory.sqlite"))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id() -> str:
    return uuid.uuid4().hex


class MemoryStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversation_owner (
                    conversation_id TEXT PRIMARY KEY,
                    owner_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_memory (
                    memory_id TEXT PRIMARY KEY,
                    owner_user_id TEXT NOT NULL,
                    scope_type TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subject_key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source_proposal_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    supersedes_memory_id TEXT,
                    provenance TEXT NOT NULL,
                    privacy_reason TEXT NOT NULL DEFAULT ''
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_subject
                ON agent_memory(owner_user_id, category, subject_key)
                WHERE status = 'active';
                CREATE TABLE IF NOT EXISTS agent_proposal (
                    proposal_id TEXT PRIMARY KEY,
                    owner_user_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subject_key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    status TEXT NOT NULL,
                    decision_label TEXT NOT NULL DEFAULT '',
                    proposed_at TEXT NOT NULL,
                    resolved_at TEXT,
                    memory_id TEXT,
                    privacy_reason TEXT NOT NULL DEFAULT '',
                    target_memory_id TEXT NOT NULL DEFAULT ''
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_pending_proposal
                ON agent_proposal(owner_user_id, conversation_id)
                WHERE status = 'pending';
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def clear(self) -> None:
        """Drop local rows. Tests use this so one process-wide file cannot leak between cases."""

        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM agent_memory")
            conn.execute("DELETE FROM agent_proposal")
            conn.execute("DELETE FROM conversation_owner")

    def claim_conversation(self, owner_user_id: str, conversation_id: str, now: datetime | None = None) -> bool:
        moment = _stamp(now or utcnow())
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT owner_user_id FROM conversation_owner WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            if row is not None:
                return row["owner_user_id"] == owner_user_id
            try:
                conn.execute(
                    """
                    INSERT INTO conversation_owner (conversation_id, owner_user_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (conversation_id, owner_user_id, moment),
                )
            except sqlite3.IntegrityError:
                winner = conn.execute(
                    "SELECT owner_user_id FROM conversation_owner WHERE conversation_id = ?",
                    (conversation_id,),
                ).fetchone()
                return winner is not None and winner["owner_user_id"] == owner_user_id
        return True

    def get_pending(
        self,
        owner_user_id: str,
        conversation_id: str,
        now: datetime | None = None,
    ) -> ProposalRecord | None:
        moment = now or utcnow()
        self._expire_pending(owner_user_id, conversation_id, moment)
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM agent_proposal
                WHERE owner_user_id = ? AND conversation_id = ? AND status = 'pending'
                """,
                (owner_user_id, conversation_id),
            ).fetchone()
        return _proposal(row) if row else None

    def list_active(self, owner_user_id: str, now: datetime | None = None) -> list[MemoryRecord]:
        moment = now or utcnow()
        self._expire_memories(owner_user_id, moment)
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM agent_memory
                WHERE owner_user_id = ? AND status = 'active'
                ORDER BY created_at
                """,
                (owner_user_id,),
            ).fetchall()
        kept: list[MemoryRecord] = []
        for row in rows:
            record = _memory(row)
            checked = validate_memory_text(record.content)
            if is_phi_block(checked):
                self._quarantine(record.memory_id, owner_user_id, moment)
                continue
            kept.append(record)
        return kept

    def list_audit(self, owner_user_id: str) -> list[ProposalRecord]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM agent_proposal
                WHERE owner_user_id = ?
                ORDER BY proposed_at
                """,
                (owner_user_id,),
            ).fetchall()
        return [_proposal(row) for row in rows]

    def list_memories(self, owner_user_id: str) -> list[MemoryRecord]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM agent_memory
                WHERE owner_user_id = ?
                ORDER BY created_at
                """,
                (owner_user_id,),
            ).fetchall()
        return [_memory(row) for row in rows]

    def has_pending(self, owner_user_id: str, conversation_id: str) -> bool:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM agent_proposal
                WHERE owner_user_id = ? AND conversation_id = ? AND status = 'pending'
                """,
                (owner_user_id, conversation_id),
            ).fetchone()
        return row is not None

    def create_proposal(
        self,
        *,
        owner_user_id: str,
        conversation_id: str,
        run_id: str,
        action: str,
        category: str,
        subject_key: str,
        content: str,
        rationale: str,
        target_memory_id: str = "",
        now: datetime | None = None,
    ) -> dict:
        if action not in ACTIONS or category not in CATEGORIES:
            return {"ok": False, "reason": "invalid", "proposal": None}
        checked = validate_memory_text(content)
        moment = _stamp(now or utcnow())
        proposal_id = _new_id()
        if not checked.allowed:
            reason = checked.reason_codes[0] if checked.reason_codes else "validator_error"
            if is_phi_block(checked):
                self._insert_proposal(
                    proposal_id=proposal_id,
                    owner_user_id=owner_user_id,
                    conversation_id=conversation_id,
                    run_id=run_id,
                    action=action,
                    category=category,
                    subject_key=subject_key,
                    content="",
                    rationale="",
                    status="blocked",
                    decision_label="blocked",
                    proposed_at=moment,
                    resolved_at=moment,
                    privacy_reason="phi_detected",
                    target_memory_id="",
                )
            return {"ok": False, "reason": reason, "proposal": None}
        if self.has_pending(owner_user_id, conversation_id):
            return {"ok": False, "reason": "pending_exists", "proposal": None}
        try:
            self._insert_proposal(
                proposal_id=proposal_id,
                owner_user_id=owner_user_id,
                conversation_id=conversation_id,
                run_id=run_id,
                action=action,
                category=category,
                subject_key=subject_key,
                content=content,
                rationale=rationale,
                status="pending",
                decision_label="",
                proposed_at=moment,
                resolved_at=None,
                privacy_reason="",
                target_memory_id=target_memory_id,
            )
        except sqlite3.IntegrityError:
            return {"ok": False, "reason": "pending_exists", "proposal": None}
        pending = self.get_pending(owner_user_id, conversation_id, now)
        return {"ok": pending is not None, "reason": "pending", "proposal": pending}

    def resolve(
        self,
        proposal_id: str,
        *,
        owner_user_id: str,
        conversation_id: str,
        label: str,
        edited_content: str | None = None,
        now: datetime | None = None,
    ) -> dict:
        moment_dt = now or utcnow()
        moment = _stamp(moment_dt)
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM agent_proposal
                WHERE proposal_id = ? AND owner_user_id = ? AND conversation_id = ?
                """,
                (proposal_id, owner_user_id, conversation_id),
            ).fetchone()
            if row is None:
                conn.rollback()
                return {"ok": False, "saved": False, "note": UNSAVED_NOTE, "memory_id": None, "status": "missing"}
            current = _proposal(row)
            if current.status != "pending":
                conn.rollback()
                saved = current.status in {"approved", "edited"} and bool(current.memory_id)
                note = SAVED_NOTE if saved else DISCARD_NOTE
                if current.status == "rejected":
                    note = REJECTED_NOTE
                return {
                    "ok": True,
                    "saved": saved,
                    "note": note,
                    "memory_id": current.memory_id,
                    "status": current.status,
                }
            if label == "edit":
                checked = validate_memory_text(edited_content or "")
                if not checked.allowed:
                    self._close(
                        conn,
                        proposal_id,
                        status="blocked",
                        decision_label="edit",
                        moment=moment,
                        content="",
                        privacy_reason="phi_detected",
                        memory_id=None,
                    )
                    conn.commit()
                    from app.agent.privacy import PRIVACY_REFUSAL

                    return {
                        "ok": True,
                        "saved": False,
                        "note": PRIVACY_REFUSAL,
                        "memory_id": None,
                        "status": "blocked",
                    }
                content = edited_content or ""
                new_status = "edited"
                action = "add" if current.action == "forget" else current.action
            elif label == "approve":
                checked = validate_memory_text(current.content)
                if not checked.allowed:
                    self._close(
                        conn,
                        proposal_id,
                        status="blocked",
                        decision_label="approve",
                        moment=moment,
                        content="",
                        privacy_reason="phi_detected",
                        memory_id=None,
                    )
                    conn.commit()
                    from app.agent.privacy import PRIVACY_REFUSAL

                    return {
                        "ok": True,
                        "saved": False,
                        "note": PRIVACY_REFUSAL,
                        "memory_id": None,
                        "status": "blocked",
                    }
                content = current.content
                new_status = "approved"
                action = current.action
            elif label == "reject":
                self._close(
                    conn,
                    proposal_id,
                    status="rejected",
                    decision_label="reject",
                    moment=moment,
                    content=current.content,
                    privacy_reason="",
                    memory_id=None,
                )
                conn.commit()
                return {
                    "ok": True,
                    "saved": False,
                    "note": REJECTED_NOTE,
                    "memory_id": None,
                    "status": "rejected",
                }
            elif label == "topic_change":
                self._close(
                    conn,
                    proposal_id,
                    status="discarded_topic_change",
                    decision_label="topic_change",
                    moment=moment,
                    content=current.content,
                    privacy_reason="",
                    memory_id=None,
                )
                conn.commit()
                return {
                    "ok": True,
                    "saved": False,
                    "note": DISCARD_NOTE,
                    "memory_id": None,
                    "status": "discarded_topic_change",
                }
            else:
                self._close(
                    conn,
                    proposal_id,
                    status="discarded_ambiguous",
                    decision_label="ambiguous",
                    moment=moment,
                    content=current.content,
                    privacy_reason="",
                    memory_id=None,
                )
                conn.commit()
                return {
                    "ok": True,
                    "saved": False,
                    "note": DISCARD_NOTE,
                    "memory_id": None,
                    "status": "discarded_ambiguous",
                }

            if action == "forget":
                target = current.target_memory_id
                if target:
                    conn.execute(
                        """
                        UPDATE agent_memory
                        SET status = 'deleted', updated_at = ?, content = ''
                        WHERE memory_id = ? AND owner_user_id = ? AND status = 'active'
                        """,
                        (moment, target, owner_user_id),
                    )
                self._close(
                    conn,
                    proposal_id,
                    status=new_status,
                    decision_label=label,
                    moment=moment,
                    content=content,
                    privacy_reason="",
                    memory_id=None,
                )
                conn.commit()
                return {
                    "ok": True,
                    "saved": False,
                    "note": FORGOT_NOTE,
                    "memory_id": None,
                    "status": new_status,
                }

            changed = conn.execute(
                """
                UPDATE agent_proposal
                SET status = ?, decision_label = ?, resolved_at = ?, content = ?
                WHERE proposal_id = ? AND status = 'pending'
                """,
                (new_status, label, moment, content, proposal_id),
            )
            if changed.rowcount != 1:
                conn.rollback()
                return {"ok": False, "saved": False, "note": UNSAVED_NOTE, "memory_id": None, "status": "conflict"}
            memory_id = _new_id()
            subject_key = current.subject_key
            prior = conn.execute(
                """
                SELECT memory_id FROM agent_memory
                WHERE owner_user_id = ? AND category = ? AND subject_key = ? AND status = 'active'
                """,
                (owner_user_id, current.category, subject_key),
            ).fetchone()
            supersedes = prior["memory_id"] if prior else None
            if supersedes:
                conn.execute(
                    """
                    UPDATE agent_memory
                    SET status = 'superseded', updated_at = ?
                    WHERE memory_id = ? AND owner_user_id = ?
                    """,
                    (moment, supersedes, owner_user_id),
                )
            days = EXPIRY_DAYS.get(current.category)
            expires = _stamp(moment_dt + timedelta(days=days)) if days else None
            conn.execute(
                """
                INSERT INTO agent_memory (
                    memory_id, owner_user_id, scope_type, scope_key, category, subject_key,
                    content, status, source_proposal_id, created_at, updated_at, expires_at,
                    supersedes_memory_id, provenance, privacy_reason
                ) VALUES (?, ?, 'user', ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, 'user_approved', '')
                """,
                (
                    memory_id,
                    owner_user_id,
                    owner_user_id,
                    current.category,
                    subject_key,
                    content,
                    proposal_id,
                    moment,
                    moment,
                    expires,
                    supersedes,
                ),
            )
            conn.execute(
                "UPDATE agent_proposal SET memory_id = ? WHERE proposal_id = ?",
                (memory_id, proposal_id),
            )
            conn.commit()
        note = EDITED_NOTE if new_status == "edited" else SAVED_NOTE
        return {"ok": True, "saved": True, "note": note, "memory_id": memory_id, "status": new_status}

    def import_legacy(
        self,
        *,
        owner_user_id: str,
        category: str,
        subject_key: str,
        content: str,
        now: datetime | None = None,
    ) -> str:
        """Load a pre-existing row without the write-time privacy gate.

        Consolidation revalidates these rows. The agent does not call this on a live turn.
        """

        moment = _stamp(now or utcnow())
        memory_id = _new_id()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_memory (
                    memory_id, owner_user_id, scope_type, scope_key, category, subject_key,
                    content, status, source_proposal_id, created_at, updated_at, expires_at,
                    supersedes_memory_id, provenance, privacy_reason
                ) VALUES (?, ?, 'user', ?, ?, ?, ?, 'active', '', ?, ?, NULL, NULL, 'legacy', '')
                """,
                (memory_id, owner_user_id, owner_user_id, category, subject_key, content, moment, moment),
            )
        return memory_id

    def supersede_duplicate(self, memory_id: str, owner_user_id: str, now: datetime | None = None) -> bool:
        moment = _stamp(now or utcnow())
        with self._lock, self._connect() as conn:
            changed = conn.execute(
                """
                UPDATE agent_memory
                SET status = 'superseded', updated_at = ?
                WHERE memory_id = ? AND owner_user_id = ? AND status = 'active'
                """,
                (moment, memory_id, owner_user_id),
            )
        return changed.rowcount == 1

    def _expire_pending(self, owner_user_id: str, conversation_id: str, now: datetime) -> None:
        cutoff = _stamp(now - timedelta(hours=PENDING_HOURS))
        moment = _stamp(now)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE agent_proposal
                SET status = 'expired', decision_label = 'expired', resolved_at = ?
                WHERE owner_user_id = ? AND conversation_id = ? AND status = 'pending'
                  AND proposed_at <= ?
                """,
                (moment, owner_user_id, conversation_id, cutoff),
            )

    def _expire_memories(self, owner_user_id: str, now: datetime) -> None:
        moment = _stamp(now)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE agent_memory
                SET status = 'expired', updated_at = ?
                WHERE owner_user_id = ? AND status = 'active'
                  AND expires_at IS NOT NULL AND expires_at <= ?
                """,
                (moment, owner_user_id, moment),
            )

    def _quarantine(self, memory_id: str, owner_user_id: str, now: datetime) -> None:
        moment = _stamp(now)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE agent_memory
                SET status = 'deleted', content = '', privacy_reason = 'phi_detected', updated_at = ?
                WHERE memory_id = ? AND owner_user_id = ?
                """,
                (moment, memory_id, owner_user_id),
            )

    def _insert_proposal(self, **fields) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_proposal (
                    proposal_id, owner_user_id, conversation_id, run_id, action, category,
                    subject_key, content, rationale, status, decision_label, proposed_at,
                    resolved_at, memory_id, privacy_reason, target_memory_id
                ) VALUES (
                    :proposal_id, :owner_user_id, :conversation_id, :run_id, :action, :category,
                    :subject_key, :content, :rationale, :status, :decision_label, :proposed_at,
                    :resolved_at, NULL, :privacy_reason, :target_memory_id
                )
                """,
                fields,
            )

    def _close(
        self,
        conn: sqlite3.Connection,
        proposal_id: str,
        *,
        status: str,
        decision_label: str,
        moment: str,
        content: str,
        privacy_reason: str,
        memory_id: str | None,
    ) -> None:
        conn.execute(
            """
            UPDATE agent_proposal
            SET status = ?, decision_label = ?, resolved_at = ?, content = ?,
                privacy_reason = ?, memory_id = ?
            WHERE proposal_id = ? AND status = 'pending'
            """,
            (status, decision_label, moment, content, privacy_reason, memory_id, proposal_id),
        )


def _proposal(row: sqlite3.Row) -> ProposalRecord:
    return ProposalRecord(
        proposal_id=row["proposal_id"],
        owner_user_id=row["owner_user_id"],
        conversation_id=row["conversation_id"],
        run_id=row["run_id"],
        action=row["action"],
        category=row["category"],
        subject_key=row["subject_key"],
        content=row["content"],
        rationale=row["rationale"],
        status=row["status"],
        decision_label=row["decision_label"],
        proposed_at=row["proposed_at"],
        resolved_at=row["resolved_at"],
        memory_id=row["memory_id"],
        privacy_reason=row["privacy_reason"],
        target_memory_id=row["target_memory_id"],
    )


def _memory(row: sqlite3.Row) -> MemoryRecord:
    return MemoryRecord(
        memory_id=row["memory_id"],
        owner_user_id=row["owner_user_id"],
        scope_type=row["scope_type"],
        scope_key=row["scope_key"],
        category=row["category"],
        subject_key=row["subject_key"],
        content=row["content"],
        status=row["status"],
        source_proposal_id=row["source_proposal_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        expires_at=row["expires_at"],
        supersedes_memory_id=row["supersedes_memory_id"],
        provenance=row["provenance"],
        privacy_reason=row["privacy_reason"],
    )
