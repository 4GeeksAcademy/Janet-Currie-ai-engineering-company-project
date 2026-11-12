"""One log line per door try. The line never includes the token."""

from __future__ import annotations

import logging
from contextvars import ContextVar
from datetime import datetime, timezone

logger = logging.getLogger("healthcore.company_tools")
request_id_var: ContextVar[str] = ContextVar("mcp_request_id", default="-")
auth_failures: dict[str, str] = {}


def write_audit(
    *,
    user_id: str,
    tool: str,
    outcome: str,
    error_code: str,
    duration_ms: int,
    resource_id: str,
) -> None:
    logger.info(
        "time=%s request_id=%s user_id=%s tool=%s outcome=%s error_code=%s duration_ms=%s resource_id=%s",
        datetime.now(timezone.utc).isoformat(),
        request_id_var.get(),
        user_id or "-",
        tool,
        outcome,
        error_code or "-",
        duration_ms,
        resource_id or "-",
    )
