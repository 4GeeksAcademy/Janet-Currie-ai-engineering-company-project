"""Read one incident from the latest upload. This tool does not change incidents."""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout

from app.store import get_incident

logger = logging.getLogger("healthcore.agent")

INCIDENT_LOOKUP_TIMEOUT_SECONDS = 3
INCIDENT_ID_RE = re.compile(r"HC-\d{6}")
INCIDENT_NOT_CONFIRMED = "That incident could not be confirmed."
STATUS_NOT_CONFIRMED = "The current status could not be confirmed."
INVALID_INCIDENT_ID = "That is not a HealthCore incident id. Use an id like HC-000006."


def lookup_incident(incident_id: str) -> dict:
    """Look up one HC-###### id. An invalid id never touches the store."""

    cleaned = (incident_id or "").strip().upper()
    if INCIDENT_ID_RE.fullmatch(cleaned) is None:
        return {"outcome": "invalid", "incident": None}
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(get_incident, cleaned)
    try:
        row = future.result(timeout=INCIDENT_LOOKUP_TIMEOUT_SECONDS)
    except FuturesTimeout:
        return {"outcome": "timeout", "incident": None}
    except Exception:
        logger.info("incident_lookup_failed")
        return {"outcome": "unavailable", "incident": None}
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    if not row:
        return {"outcome": "not_found", "incident": None}
    return {"outcome": "found", "incident": row}


def format_incident(row: dict) -> str:
    return (
        f"Incident {row.get('incident_id', '')} is {row.get('status', '')}. "
        f"Category: {row.get('category', '')}. "
        f"Clinic: {row.get('clinic_id', '')}. "
        f"Country: {row.get('country', '')}. "
        f"Date: {row.get('date', '')}."
    )


def incident_answer(outcome: str, row: dict | None) -> str:
    if outcome == "found" and row:
        return format_incident(row)
    if outcome in {"timeout", "unavailable"}:
        return STATUS_NOT_CONFIRMED
    return INCIDENT_NOT_CONFIRMED
