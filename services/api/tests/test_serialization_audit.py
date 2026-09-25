"""Serialization audit: route matrix, payload secrets, write-schema isolation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, get_args, get_origin

from fastapi.routing import APIRoute

from app.auth.security import create_reset_token
from app.auth.service import create_password_reset, get_user_by_email, get_user_by_id
from app.main import app
from tests.helpers import (
    SCRIPTS,
    auth_header,
    client,
    login,
    register,
    reset_inventory_db,
)

FRAMEWORK_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}

JSON_ROUTES: dict[tuple[str, str], str] = {
    ("GET", "/health"): "HealthResponse",
    ("POST", "/auth/login"): "TokenResponse",
    ("GET", "/auth/me"): "MeResponse",
    ("POST", "/auth/forgot-password"): "MessageResponse",
    ("POST", "/auth/reset-password"): "MessageResponse",
    ("POST", "/auth/change-password"): "MessageResponse",
    ("GET", "/users"): "UserPublic",
    ("POST", "/users"): "UserRegisteredResponse",
    ("GET", "/users/{user_id}"): "UserPublic",
    ("PUT", "/users/{user_id}"): "UserPublic",
    ("GET", "/profiles/me"): "ProfilePublic",
    ("PUT", "/profiles/me"): "ProfilePublic",
    ("POST", "/api/incidents/analyze"): "IncidentAnalysisResponse",
    ("POST", "/suppliers"): "Supplier",
    ("GET", "/suppliers"): "Supplier",
    ("GET", "/suppliers/{supplier_id}"): "Supplier",
    ("PATCH", "/suppliers/{supplier_id}"): "Supplier",
    ("PATCH", "/suppliers/{supplier_id}/rate"): "Supplier",
    ("PATCH", "/suppliers/{supplier_id}/status"): "Supplier",
    ("GET", "/inventory/products"): "MedicalSupplyPublic",
    ("POST", "/inventory/products"): "MedicalSupplyPublic",
    ("GET", "/inventory/products/{supply_id}"): "MedicalSupplyPublic",
    ("POST", "/inventory/orders/inbound"): "DeliveryPublic",
    ("POST", "/inventory/orders/outbound"): "ConsumptionPublic",
    ("GET", "/inventory/orders"): "OrderMovement",
}

SPECIAL_ROUTES: dict[tuple[str, str], str] = {
    ("DELETE", "/users/{user_id}"): "204",
    ("GET", "/api/incidents/results/export"): "csv",
}

SECRET_KEYS = {"password", "hashed_password", "jti"}
GLOVES = {
    "name": "Nitrile gloves (box of 100)",
    "sku": "HCR-PPE-001",
    "category": "ppe",
    "unit": "box",
    "country": "US",
}


def _inner_model_name(response_model: Any) -> str | None:
    if response_model is None:
        return None
    origin = get_origin(response_model)
    if origin is dict or response_model is dict:
        return "dict"
    if origin is list:
        inner = get_args(response_model)[0]
        return getattr(inner, "__name__", str(inner))
    return getattr(response_model, "__name__", str(response_model))


def _application_api_routes() -> list[APIRoute]:
    routes: list[APIRoute] = []

    def walk(items: list[Any]) -> None:
        for route in items:
            if isinstance(route, APIRoute):
                if route.path not in FRAMEWORK_PATHS:
                    routes.append(route)
            elif getattr(route, "original_router", None) is not None:
                walk(route.original_router.routes)

    walk(list(app.router.routes))
    return routes


def _assert_no_secrets(payload: object) -> None:
    if isinstance(payload, dict):
        overlap = SECRET_KEYS & set(payload)
        assert not overlap, f"secret fields leaked: {overlap}"
        for value in payload.values():
            _assert_no_secrets(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_secrets(item)


def test_runtime_routes_match_audit_matrix() -> None:
    seen: set[tuple[str, str]] = set()
    for route in _application_api_routes():
        methods = {m for m in route.methods if m not in {"HEAD", "OPTIONS"}}
        for method in methods:
            key = (method, route.path)
            seen.add(key)
            name = _inner_model_name(route.response_model)
            if key in JSON_ROUTES:
                assert name == JSON_ROUTES[key], f"{key} expected {JSON_ROUTES[key]}, got {name}"
                assert route.response_model is not dict
                assert get_origin(route.response_model) is not dict
                assert name not in {None, "dict"}
            elif key in SPECIAL_ROUTES:
                assert route.response_model is None
            else:
                raise AssertionError(f"unexpected application route {key}")
    expected = set(JSON_ROUTES) | set(SPECIAL_ROUTES)
    assert seen == expected


def test_openapi_documents_special_and_json_contracts() -> None:
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    login_ref = paths["/auth/login"]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert login_ref.endswith("TokenResponse")
    register_ref = paths["/users"]["post"]["responses"]["201"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert register_ref.endswith("UserRegisteredResponse")
    orders_ref = paths["/inventory/orders"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    item = orders_ref.get("items") or {}
    assert (item.get("$ref") or "").endswith("OrderMovement")
    delete = paths["/users/{user_id}"]["delete"]["responses"]
    assert "204" in delete
    export_content = paths["/api/incidents/results/export"]["get"]["responses"]["200"][
        "content"
    ]
    assert "text/csv" in export_content
    assert client.get("/docs").status_code == 200


def test_public_auth_payloads_omit_email_and_secrets() -> None:
    created = register(email="serial@healthcore.example", password="secret123")
    assert created.status_code == 201
    body = created.json()
    assert set(body) == {"id", "role", "is_active"}
    _assert_no_secrets(body)
    assert "email" not in body

    token_body = login(email="serial@healthcore.example", password="secret123").json()
    assert set(token_body) == {"access_token", "token_type"}
    _assert_no_secrets(token_body)
    assert "email" not in token_body

    forgot = client.post(
        "/auth/forgot-password", json={"email": "serial@healthcore.example"}
    )
    assert forgot.status_code == 200
    assert set(forgot.json()) == {"detail"}
    _assert_no_secrets(forgot.json())
    assert "email" not in forgot.json()

    user = get_user_by_email("serial@healthcore.example")
    jti = create_password_reset(
        user["id"], datetime.now(timezone.utc) + timedelta(minutes=30)
    )
    reset_token = create_reset_token(user_id=user["id"], jti=jti)
    reset = client.post(
        "/auth/reset-password",
        json={"token": reset_token, "new_password": "secret123"},
    )
    assert reset.status_code == 200
    assert set(reset.json()) == {"detail"}
    _assert_no_secrets(reset.json())
    assert "email" not in reset.json()
    assert "token" not in reset.json()

    headers = {
        "Authorization": (
            "Bearer "
            + login(email="serial@healthcore.example", password="secret123").json()[
                "access_token"
            ]
        )
    }
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["email"] == "serial@healthcore.example"
    _assert_no_secrets(me_body)

    change = client.post(
        "/auth/change-password",
        headers=headers,
        json={"current_password": "secret123", "new_password": "secret123"},
    )
    assert change.status_code == 200
    assert set(change.json()) == {"detail"}
    _assert_no_secrets(change.json())


def test_write_schemas_reject_server_managed_fields() -> None:
    reset_inventory_db()
    headers = auth_header(email="writer@healthcore.example", password="secret123")
    user = get_user_by_email("writer@healthcore.example")
    assert user is not None

    registered = client.post(
        "/users",
        json={
            "email": "extra@healthcore.example",
            "password": "secret123",
            "hashed_password": "not-a-hash",
            "id": 999,
        },
    )
    assert registered.status_code == 201
    assert registered.json()["id"] != 999
    stored = get_user_by_email("extra@healthcore.example")
    assert stored is not None
    assert stored["hashed_password"] != "not-a-hash"
    assert str(stored["hashed_password"]).startswith("$2")

    updated = client.put(
        f"/users/{user['id']}",
        headers=headers,
        json={"hashed_password": "still-not-a-hash", "id": 1},
    )
    assert updated.status_code == 200
    again = get_user_by_id(user["id"])
    assert again is not None
    assert again["hashed_password"] != "still-not-a-hash"

    profile = client.put(
        "/profiles/me",
        headers=headers,
        json={"name": "Writer", "id": 50, "user_id": 50},
    )
    assert profile.status_code == 200
    assert profile.json()["id"] != 50
    assert profile.json()["user_id"] == user["id"]

    product = client.post(
        "/inventory/products",
        headers=headers,
        json={**GLOVES, "id": 77, "current_stock": 999},
    )
    assert product.status_code == 201
    assert product.json()["id"] != 77
    assert product.json()["current_stock"] == 0
    supply_id = product.json()["id"]

    inbound = client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 2,
            "vendor_name": "MedLine Industries",
            "clinic_id": 1,
            "user_uuid": "999",
        },
    )
    assert inbound.status_code == 201
    assert inbound.json()["user_uuid"] != "999"
    assert inbound.json()["user_uuid"] == str(user["id"])

    created_at = "2000-01-01T00:00:00+00:00"
    supplier = client.post(
        "/suppliers",
        headers=headers,
        json={
            "name": "Write Schema Co",
            "country": "USA",
            "categories": ["laboratory_services"],
            "monthly_rate": 10,
            "currency": "USD",
            "status": "active",
            "id": 42,
            "updated_at": created_at,
        },
    )
    assert supplier.status_code == 201
    assert supplier.json()["id"] != 42
    assert supplier.json()["updated_at"] != created_at


def test_analyze_response_matches_incident_schema() -> None:
    headers = auth_header(email="incidents@healthcore.example")
    data = (SCRIPTS / "incidents-healthcore.csv").read_bytes()
    response = client.post(
        "/api/incidents/analyze",
        headers=headers,
        files={"file": ("incidents-healthcore.csv", data, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {
        "source_file",
        "total_records",
        "valid_count",
        "invalid_count",
        "invalid_breakdown",
        "category_counts",
        "status_counts",
        "country_counts",
        "satisfaction",
    }
    _assert_no_secrets(body)
    assert "PAT-" not in response.text
