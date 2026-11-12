"""In-memory store for the most recent incident analysis (Phase 2 demo)."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Optional

SAFE_INCIDENT_FIELDS = (
    "incident_id",
    "date",
    "clinic_id",
    "country",
    "category",
    "status",
)


@dataclass
class StoredAnalysis:
    summary: object
    incidents: dict[str, dict[str, str]]


_lock = Lock()
_latest: Optional[StoredAnalysis] = None


def _field(record: object, name: str) -> str:
    if isinstance(record, dict):
        value = record.get(name, "")
    else:
        value = getattr(record, name, "")
    return str(value or "").strip()


def _safe_incident(record: object) -> dict[str, str] | None:
    incident_id = _field(record, "incident_id").upper()
    if not incident_id:
        return None
    row = {name: _field(record, name) for name in SAFE_INCIDENT_FIELDS}
    row["incident_id"] = incident_id
    return row


def save_analysis(summary: object, records: list | None = None) -> None:
    """Save the latest totals and the safe fields from that same upload."""

    global _latest
    incidents: dict[str, dict[str, str]] = {}
    for record in records or []:
        row = _safe_incident(record)
        if row is not None:
            incidents[row["incident_id"]] = row
    with _lock:
        _latest = StoredAnalysis(summary=summary, incidents=incidents)


def get_latest() -> Optional[StoredAnalysis]:
    with _lock:
        return _latest


def get_incident(incident_id: str) -> dict[str, str] | None:
    """Return one saved incident, or nothing when that id was not in the latest upload."""

    key = (incident_id or "").strip().upper()
    with _lock:
        if _latest is None or not key:
            return None
        row = _latest.incidents.get(key)
        return dict(row) if row else None


def clear() -> None:
    """Test helper to reset stored results."""
    global _latest
    with _lock:
        _latest = None
