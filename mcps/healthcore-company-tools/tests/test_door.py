"""The tool door rejects a bad token and only reads."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx2
import jwt
import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from healthcore_company_tools.auth import AUDIENCE, ISSUER
from healthcore_company_tools.server import create_app, guard_inventory

SECRET = "test-secret-for-the-healthcore-door"
CLOSED = {
    "incident_id": "HC-000006",
    "date": "2026-01-15",
    "clinic_id": "UK-MAN-01",
    "country": "UK",
    "category": "CLINICAL_CARE",
    "status": "CLOSED",
    "patient_id": "PAT-900006",
    "description": "Closed without a satisfaction score recorded.",
}
GLOVES = {
    "id": 4,
    "name": "Nitrile gloves",
    "sku": "GLV-4",
    "category": "ppe",
    "unit": "box",
    "country": "UK",
    "current_stock": 12,
}


def setup_module() -> None:
    import os

    os.environ["SECRET_KEY"] = SECRET


def _token(
    scope: str = "incidents:read inventory:read",
    *,
    audience: str = AUDIENCE,
    issuer: str = ISSUER,
    expired: bool = False,
    extra: dict | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "7",
        "iss": issuer,
        "aud": audience,
        "scope": scope,
        "exp": now + timedelta(minutes=-5 if expired else 30),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, SECRET, algorithm="HS256")


def _transport(app, token: str | None):
    def factory(*, headers=None, auth=None, follow_redirects=True, timeout=None, **_kwargs):
        return httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app),
            base_url="http://testserver",
            headers=headers,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
        )

    headers = {"Authorization": f"Bearer {token}"} if token else None
    return StreamableHttpTransport(
        "http://testserver/mcp",
        headers=headers,
        httpx_client_factory=factory,
    )


def _result_text(result) -> str:
    if getattr(result, "data", None) is not None:
        return str(result.data)
    chunks = []
    for block in getattr(result, "content", []) or []:
        chunks.append(getattr(block, "text", str(block)))
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        chunks.append(str(structured))
    return "\n".join(chunks)


def _data(result) -> dict:
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured
    if hasattr(data, "model_dump"):
        return data.model_dump()
    raise AssertionError(f"no structured result: {result!r}")


def test_missing_token_cannot_list_or_call_tools(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app()

    async def scenario():
        async with app.router.lifespan_context(app):
            with pytest.raises(Exception):
                async with Client(_transport(app, None)) as client:
                    await client.list_tools()
            transport = httpx2.ASGITransport(app=app)
            async with httpx2.AsyncClient(transport=transport, base_url="http://testserver") as http:
                response = await http.post(
                    "/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "get_incident_status",
                            "arguments": {"incident_id": "HC-000006"},
                        },
                    },
                )
        return response.status_code

    caplog.set_level(logging.INFO, logger="healthcore.company_tools")
    status_code = asyncio.run(scenario())
    assert status_code == 401
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "outcome=refused" in text
    assert "AUTH_REQUIRED" in text


def test_broken_expired_and_wrong_audience_tokens_are_rejected(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app()

    async def attempt(token: str) -> int:
        async with app.router.lifespan_context(app):
            transport = httpx2.ASGITransport(app=app)
            async with httpx2.AsyncClient(transport=transport, base_url="http://testserver") as http:
                response = await http.post(
                    "/mcp",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                )
        return response.status_code

    caplog.set_level(logging.INFO, logger="healthcore.company_tools")
    assert asyncio.run(attempt("not-a-token")) == 401
    assert asyncio.run(attempt(_token(expired=True))) == 401
    assert asyncio.run(attempt(_token(audience="someone-else"))) == 401
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "TOKEN_EXPIRED" in text
    assert "INVALID_TOKEN" in text
    assert SECRET not in text
    assert "not-a-token" not in text


def test_staff_token_reads_one_incident_without_private_fields(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        "healthcore_company_tools.readers.fetch_incident",
        lambda incident_id: CLOSED if incident_id == "HC-000006" else None,
    )
    app = create_app()

    async def scenario():
        async with app.router.lifespan_context(app):
            async with Client(_transport(app, _token())) as client:
                listed = await client.list_tools()
                found = await client.call_tool(
                    "get_incident_status",
                    {"incident_id": "HC-000006"},
                )
                missing = await client.call_tool(
                    "get_incident_status",
                    {"incident_id": "HC-999999"},
                )
        return listed, found, missing

    caplog.set_level(logging.INFO, logger="healthcore.company_tools")
    listed, found, missing = asyncio.run(scenario())
    names = {tool.name for tool in listed}
    assert names == {"get_incident_status", "query_inventory"}
    found_data = _data(found)
    assert found_data["status"] == "CLOSED"
    blob = _result_text(found) + str(found_data)
    assert "PAT-" not in blob
    assert "patient_id" not in blob
    missing_data = _data(missing)
    assert missing_data["outcome"] == "not_found"
    assert missing_data["error_code"] == "INCIDENT_NOT_FOUND"
    assert not missing_data.get("status")
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "tool=get_incident_status" in text
    assert "user_id=7" in text
    assert "HC-000006" in text
    assert SECRET not in text


def test_inventory_read_and_read_only_guard(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls = {"write": 0}

    def fetch(product_id):
        if product_id is None:
            return [GLOVES]
        if product_id == 4:
            return [GLOVES]
        return None

    def forbidden(*_args, **_kwargs):
        calls["write"] += 1
        raise AssertionError("a stock change must not call a write")

    monkeypatch.setattr("healthcore_company_tools.readers.fetch_inventory", fetch)
    monkeypatch.setattr("healthcore_company_tools.readers.create_supply", forbidden)
    monkeypatch.setattr("healthcore_company_tools.readers.create_delivery", forbidden)
    monkeypatch.setattr("healthcore_company_tools.readers.create_consumption", forbidden)
    app = create_app()

    async def scenario():
        token = _token(scope="inventory:read")
        async with app.router.lifespan_context(app):
            async with Client(_transport(app, token)) as client:
                listed = await client.call_tool("query_inventory", {"action": "list"})
                one = await client.call_tool(
                    "query_inventory",
                    {"action": "get", "product_id": 4},
                )
                missing = await client.call_tool(
                    "query_inventory",
                    {"action": "get", "product_id": 99},
                )
                refused = await client.call_tool(
                    "query_inventory",
                    {"action": "create", "product_id": 4},
                )
                blocked = await client.call_tool(
                    "get_incident_status",
                    {"incident_id": "HC-000006"},
                )
        return listed, one, missing, refused, blocked

    caplog.set_level(logging.INFO, logger="healthcore.company_tools")
    listed, one, missing, refused, blocked = asyncio.run(scenario())
    assert _data(listed)["products"][0]["name"] == "Nitrile gloves"
    assert _data(one)["products"][0]["current_stock"] == 12
    assert _data(missing)["error_code"] == "INVENTORY_NOT_FOUND"
    assert _data(refused)["error_code"] == "INVENTORY_READ_ONLY"
    assert _data(blocked)["error_code"] == "INSUFFICIENT_SCOPE"
    assert calls["write"] == 0
    assert guard_inventory("receive") == "INVENTORY_READ_ONLY"
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "INVENTORY_READ_ONLY" in text
    assert "INSUFFICIENT_SCOPE" in text
    assert SECRET not in text
