"""Read one incident through the HealthCore tool door."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from contextvars import ContextVar

from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger("healthcore.agent")
staff_token_var: ContextVar[str | None] = ContextVar("agent_staff_token", default=None)
SAFE_FIELDS = ("incident_id", "date", "clinic_id", "country", "category", "status")

INCIDENT_LOOKUP_TIMEOUT_SECONDS = 3
INCIDENT_ID_RE = re.compile(r"HC-\d{6}")
INCIDENT_NOT_CONFIRMED = "That incident could not be confirmed."
STATUS_NOT_CONFIRMED = "The current status could not be confirmed."
INVALID_INCIDENT_ID = "That is not a HealthCore incident id. Use an id like HC-000006."


def mcp_url() -> str:
    base = os.getenv("MCP_URL", "http://127.0.0.1:8001").rstrip("/")
    if base.endswith("/mcp"):
        return base
    return f"{base}/mcp"


def _payload(raw: object) -> dict:
    if isinstance(raw, tuple) and len(raw) == 2:
        content, artifact = raw
        structured = getattr(artifact, "structured_content", None)
        if isinstance(structured, dict):
            return structured
        raw = content
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("The incident tool returned an unexpected result.")


def call_incident_tool(incident_id: str, token: str) -> dict:
    """Ask the door for one incident. The token is a header, not graph state."""

    async def _call() -> dict:
        client = MultiServerMCPClient(
            {
                "healthcore": {
                    "transport": "streamable_http",
                    "url": mcp_url(),
                    "headers": {"Authorization": f"Bearer {token}"},
                    "timeout": INCIDENT_LOOKUP_TIMEOUT_SECONDS,
                }
            }
        )
        tools = await client.get_tools(server_name="healthcore")
        tool = next(item for item in tools if item.name == "get_incident_status")
        return _payload(await tool.ainvoke({"incident_id": incident_id}))

    return asyncio.run(_call())


def _row_from_payload(payload: dict) -> dict | None:
    if payload.get("outcome") != "found":
        return None
    return {field: str(payload.get(field) or "") for field in SAFE_FIELDS}


def lookup_incident(incident_id: str) -> dict:
    """Look up one HC-###### id through the tool door."""

    cleaned = (incident_id or "").strip().upper()
    if INCIDENT_ID_RE.fullmatch(cleaned) is None:
        return {"outcome": "invalid", "incident": None}
    token = staff_token_var.get()
    if not token:
        return {"outcome": "unavailable", "incident": None}
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(call_incident_tool, cleaned, token)
    try:
        payload = future.result(timeout=INCIDENT_LOOKUP_TIMEOUT_SECONDS)
    except FuturesTimeout:
        return {"outcome": "timeout", "incident": None}
    except Exception:
        logger.info("incident_lookup_failed")
        return {"outcome": "unavailable", "incident": None}
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    outcome = str(payload.get("outcome") or "unavailable")
    if outcome == "timeout":
        return {"outcome": "timeout", "incident": None}
    if outcome != "found":
        return {"outcome": "not_found" if outcome == "not_found" else "unavailable", "incident": None}
    return {"outcome": "found", "incident": _row_from_payload(payload)}


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
