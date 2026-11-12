"""HealthCore tool door. Two reads, no writes, staff token required."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Literal

from fastmcp import FastMCP
from mcpauth.exceptions import BearerAuthExceptionCode
from pydantic import BaseModel, Field

from healthcore_company_tools.audit import auth_failures, request_id_var, write_audit
from healthcore_company_tools.auth import (
    AUDIENCE,
    INCIDENT_SCOPE,
    INVENTORY_SCOPE,
    build_mcp_auth,
    verify_staff_token,
)
from healthcore_company_tools import readers

logger = logging.getLogger("healthcore.company_tools")

STREAMABLE_HTTP_PATH = "/mcp"
DEFAULT_PORT = 8001
LOOKUP_TIMEOUT_SECONDS = 3
INCIDENT_FIELDS = (
    "incident_id",
    "date",
    "clinic_id",
    "country",
    "category",
    "status",
)
PRODUCT_FIELDS = (
    "id",
    "name",
    "sku",
    "category",
    "unit",
    "country",
    "current_stock",
)
WRITE_ACTIONS = {"create", "update", "delete", "receive", "use"}
AUTH_ERROR_CODES = {
    BearerAuthExceptionCode.MISSING_AUTH_HEADER.value: "AUTH_REQUIRED",
    BearerAuthExceptionCode.MISSING_BEARER_TOKEN.value: "AUTH_REQUIRED",
    BearerAuthExceptionCode.INVALID_AUTH_HEADER_FORMAT.value: "INVALID_TOKEN",
    BearerAuthExceptionCode.INVALID_TOKEN.value: "INVALID_TOKEN",
    BearerAuthExceptionCode.INVALID_ISSUER.value: "INVALID_TOKEN",
    BearerAuthExceptionCode.INVALID_AUDIENCE.value: "INVALID_TOKEN",
    BearerAuthExceptionCode.MISSING_REQUIRED_SCOPES.value: "INSUFFICIENT_SCOPE",
    "invalid_token": "INVALID_TOKEN",
}


class IncidentStatus(BaseModel):
    """Saved incident fields. This result has no patient id and no description."""

    outcome: Literal["found", "not_found", "timeout", "unavailable", "invalid"]
    error_code: str | None = None
    incident_id: str | None = None
    date: str | None = None
    clinic_id: str | None = None
    country: str | None = None
    category: str | None = None
    status: str | None = None


class ProductRecord(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    unit: str
    country: str
    current_stock: int


class InventoryRead(BaseModel):
    products: list[ProductRecord] = Field(default_factory=list)
    error_code: str | None = None


def guard_inventory(action: str) -> str | None:
    """Refuse a stock change before any write function runs."""

    if action in WRITE_ACTIONS:
        return "INVENTORY_READ_ONLY"
    return None


def _user_id() -> str:
    info = mcp_auth.auth_info
    if info is None or not info.subject:
        return "-"
    return str(info.subject)


def _has_scope(scope: str) -> bool:
    info = mcp_auth.auth_info
    return info is not None and scope in info.scopes


def _call_with_timeout(func, *args):
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(func, *args)
    try:
        return future.result(timeout=LOOKUP_TIMEOUT_SECONDS), None
    except FuturesTimeout:
        return None, "UPSTREAM_TIMEOUT"
    except Exception:
        logger.info("door_reader_failed tool_error=UPSTREAM_UNAVAILABLE")
        return None, "UPSTREAM_UNAVAILABLE"
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def _safe_incident(row: dict) -> dict:
    return {field: str(row.get(field, "")) for field in INCIDENT_FIELDS}


def _safe_product(row: dict) -> ProductRecord:
    return ProductRecord(**{field: row[field] for field in PRODUCT_FIELDS})


mcp = FastMCP(
    "HealthCore company tools",
    instructions=(
        "Read one saved HealthCore incident or read clinic stock. "
        "This door does not create incidents, change a status, or change stock."
    ),
    mask_error_details=True,
)
mcp_auth = build_mcp_auth()


@mcp.tool(
    description=(
        "Read one incident saved from the latest uploaded CSV. "
        "Use this when the question has an id like HC-000006. "
        "It does not create an incident and it does not change a status. "
        "Required scope: incidents:read. "
        "Input: incident_id. "
        "Output: outcome, error_code, incident_id, date, clinic_id, country, category, status."
    ),
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    run_in_thread=False,
)
def get_incident_status(incident_id: str) -> IncidentStatus:
    started = time.perf_counter()
    cleaned = (incident_id or "").strip().upper()
    resource_id = cleaned
    if not _has_scope(INCIDENT_SCOPE):
        result = IncidentStatus(outcome="invalid", error_code="INSUFFICIENT_SCOPE")
    elif len(cleaned) != 9 or not cleaned.startswith("HC-") or not cleaned[3:].isdigit():
        result = IncidentStatus(
            outcome="invalid",
            error_code="VALIDATION_ERROR",
            incident_id=cleaned or None,
        )
    else:
        row, error_code = _call_with_timeout(readers.fetch_incident, cleaned)
        if error_code == "UPSTREAM_TIMEOUT":
            result = IncidentStatus(
                outcome="timeout",
                error_code="UPSTREAM_TIMEOUT",
                incident_id=cleaned,
            )
        elif error_code:
            result = IncidentStatus(
                outcome="unavailable",
                error_code=error_code,
                incident_id=cleaned,
            )
        elif not row:
            result = IncidentStatus(
                outcome="not_found",
                error_code="INCIDENT_NOT_FOUND",
                incident_id=cleaned,
            )
        else:
            safe = _safe_incident(row)
            result = IncidentStatus(outcome="found", error_code=None, **safe)
    write_audit(
        user_id=_user_id(),
        tool="get_incident_status",
        outcome=result.outcome,
        error_code=result.error_code or "",
        duration_ms=round((time.perf_counter() - started) * 1000),
        resource_id=resource_id,
    )
    return result


@mcp.tool(
    description=(
        "Read clinic products. Use list to see every product, or get with a numeric product id. "
        "It does not create, update, delete, receive, or use stock. "
        "A stock change returns INVENTORY_READ_ONLY and does not change anything. "
        "Required scope: inventory:read. "
        "Input: action and optional product_id. "
        "Output: products (id, name, sku, category, unit, country, current_stock) or error_code."
    ),
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    run_in_thread=False,
)
def query_inventory(
    action: Literal["list", "get", "create", "update", "delete", "receive", "use"],
    product_id: int | None = None,
) -> InventoryRead:
    started = time.perf_counter()
    resource_id = "" if product_id is None else str(product_id)
    refusal = guard_inventory(action)
    if refusal:
        result = InventoryRead(error_code=refusal)
        outcome = "refused"
    elif not _has_scope(INVENTORY_SCOPE):
        result = InventoryRead(error_code="INSUFFICIENT_SCOPE")
        outcome = "refused"
    elif action == "list":
        rows, error_code = _call_with_timeout(readers.fetch_inventory, None)
        if error_code:
            result = InventoryRead(error_code=error_code)
            outcome = "unavailable"
        else:
            result = InventoryRead(products=[_safe_product(row) for row in (rows or [])])
            outcome = "found"
    elif action == "get":
        if product_id is None:
            result = InventoryRead(error_code="VALIDATION_ERROR")
            outcome = "invalid"
        else:
            rows, error_code = _call_with_timeout(readers.fetch_inventory, product_id)
            if error_code:
                result = InventoryRead(error_code=error_code)
                outcome = "unavailable"
            elif not rows:
                result = InventoryRead(error_code="INVENTORY_NOT_FOUND")
                outcome = "not_found"
            else:
                result = InventoryRead(products=[_safe_product(row) for row in rows])
                outcome = "found"
    else:
        result = InventoryRead(error_code="INVENTORY_READ_ONLY")
        outcome = "refused"
    write_audit(
        user_id=_user_id(),
        tool="query_inventory",
        outcome=outcome,
        error_code=result.error_code or "",
        duration_ms=round((time.perf_counter() - started) * 1000),
        resource_id=resource_id,
    )
    return result


class _AuditMiddleware:
    """Log an auth refusal without reading a successful stream."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        headers = {
            key.decode().lower(): value.decode()
            for key, value in scope.get("headers", [])
        }
        request_id = headers.get("x-request-id") or uuid.uuid4().hex
        request_token = request_id_var.set(request_id)
        status = {"code": 200}
        chunks: list[bytes] = []

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            elif message["type"] == "http.response.body" and status["code"] in {401, 403}:
                chunks.append(message.get("body") or b"")
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            if status["code"] in {401, 403}:
                hinted = auth_failures.pop(request_id, "")
                write_audit(
                    user_id="-",
                    tool="auth",
                    outcome="refused",
                    error_code=hinted or _auth_error_code(b"".join(chunks), status["code"]),
                    duration_ms=round((time.perf_counter() - started) * 1000),
                    resource_id="-",
                )
            request_id_var.reset(request_token)


def _auth_error_code(body: bytes, status_code: int) -> str:
    try:
        payload = json.loads(body.decode() or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = {}
    raw = str(payload.get("error") or "")
    if status_code == 401 and raw == "invalid_token" and "expired" in body.decode(errors="ignore").lower():
        return "TOKEN_EXPIRED"
    return AUTH_ERROR_CODES.get(raw, "AUTH_REQUIRED" if status_code == 401 else "INSUFFICIENT_SCOPE")


def create_app():
    """Starlette app for Streamable HTTP. The path is ``/mcp``."""

    from starlette.middleware import Middleware

    auth_middleware = mcp_auth.bearer_auth_middleware(
        verify_staff_token,
        audience=AUDIENCE,
    )
    return mcp.http_app(
        path=STREAMABLE_HTTP_PATH,
        transport="streamable-http",
        middleware=[Middleware(_AuditMiddleware), Middleware(auth_middleware)],
    )


def main() -> None:
    import uvicorn

    port = int(os.getenv("MCP_PORT", str(DEFAULT_PORT)))
    uvicorn.run(create_app(), host="127.0.0.1", port=port)
