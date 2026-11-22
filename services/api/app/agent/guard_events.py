"""Sanitized block and redirect records. Staff text never goes in this log."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

GUARDS = ("intake", "scope", "external", "output")
CATEGORIES = ("structural", "content", "security")
ACTIONS = ("block", "redirect")

_lock = threading.Lock()


def session_id() -> str:
    return os.environ.get("AGENT_GUARD_SESSION", "local")


def log_path() -> Path:
    override = os.environ.get("AGENT_GUARD_LOG")
    if override:
        path = Path(override)
    else:
        path = Path(__file__).resolve().parents[2] / "data" / "agent_guard_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def record_event(
    *,
    run_id: str,
    guard: str,
    reason_code: str,
    action: str,
    category: str,
) -> None:
    """Append one decision. A logging failure must not change the staff response."""

    if guard not in GUARDS or category not in CATEGORIES or action not in ACTIONS:
        guard, category, action = "output", "structural", "block"
        reason_code = "malformed_event"
    row = {
        "session_id": session_id(),
        "run_id": run_id or "",
        "guard": guard,
        "reason_code": reason_code or "unspecified",
        "action": action,
        "category": category,
    }
    try:
        line = json.dumps(row, sort_keys=True)
        with _lock:
            with log_path().open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
    except Exception:
        return


def summary(path: Path | None = None, session: str | None = None) -> dict:
    """Count one session. Missing guards and categories are zero."""

    chosen = session if session is not None else session_id()
    by_guard = {guard: {category: 0 for category in CATEGORIES} for guard in GUARDS}
    by_category = {category: 0 for category in CATEGORIES}
    total = 0
    source = path or log_path()
    if source.exists():
        for line in source.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("session_id") != chosen:
                continue
            guard = row.get("guard")
            category = row.get("category")
            if guard not in by_guard or category not in by_category:
                continue
            by_guard[guard][category] += 1
            by_category[category] += 1
            total += 1
    return {
        "session_id": chosen,
        "session_boundary": "AGENT_GUARD_SESSION plus AGENT_GUARD_LOG",
        "total": total,
        "counts_by_category": by_category,
        "counts_by_guard": by_guard,
    }
