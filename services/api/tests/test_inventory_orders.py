"""Inbound/outbound inventory movements."""

from __future__ import annotations

import pytest

from tests.helpers import auth_header, client, reset_inventory_db

GLOVES = {
    "name": "Nitrile gloves (box of 100)",
    "sku": "HCR-PPE-001",
    "category": "ppe",
    "unit": "box",
    "country": "US",
}


@pytest.fixture(autouse=True)
def _reset_inventory() -> None:
    reset_inventory_db()


def _create_supply(headers: dict) -> int:
    return client.post("/inventory/products", headers=headers, json=GLOVES).json()["id"]


def _inbound(headers: dict, supply_id: int, quantity: int = 10) -> None:
    response = client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": quantity,
            "vendor_name": "MedLine Industries",
            "clinic_id": 1,
        },
    )
    assert response.status_code == 201


def test_orders_require_auth() -> None:
    assert client.get("/inventory/orders").status_code == 401
    assert client.post("/inventory/orders/inbound", json={}).status_code == 401
    assert client.post("/inventory/orders/outbound", json={}).status_code == 401


def test_inbound_stores_clinic_timestamp_and_user() -> None:
    headers = auth_header()
    supply_id = _create_supply(headers)
    response = client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 8,
            "vendor_name": "MedLine Industries",
            "clinic_id": 4,
            "user_uuid": "999",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["quantity"] == 8
    assert body["clinic_id"] == 4
    assert body["vendor_name"] == "MedLine Industries"
    assert body["user_uuid"] != "999"
    assert body["created_at"]


def test_consumptions_subtract_and_both_types_work() -> None:
    headers = auth_header()
    supply_id = _create_supply(headers)
    _inbound(headers, supply_id, 20)
    clinical = client.post(
        "/inventory/orders/outbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 5,
            "consumption_type": "clinical_use",
            "clinic_id": 1,
        },
    )
    waste = client.post(
        "/inventory/orders/outbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 3,
            "consumption_type": "expiry_waste",
            "clinic_id": 2,
        },
    )
    assert clinical.status_code == 201
    assert waste.status_code == 201
    stock = client.get(f"/inventory/products/{supply_id}", headers=headers).json()
    assert stock["current_stock"] == 12


def test_outbound_equal_to_stock_leaves_zero() -> None:
    headers = auth_header()
    supply_id = _create_supply(headers)
    _inbound(headers, supply_id, 7)
    response = client.post(
        "/inventory/orders/outbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 7,
            "consumption_type": "clinical_use",
            "clinic_id": 1,
        },
    )
    assert response.status_code == 201
    assert client.get(f"/inventory/products/{supply_id}", headers=headers).json()["current_stock"] == 0


def test_over_consumption_returns_400_and_does_not_write() -> None:
    headers = auth_header()
    supply_id = _create_supply(headers)
    _inbound(headers, supply_id, 5)
    response = client.post(
        "/inventory/orders/outbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 6,
            "consumption_type": "clinical_use",
            "clinic_id": 1,
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Insufficient stock for supply 'Nitrile gloves (box of 100)'. Available: 5, requested: 6."
    )
    assert client.get(f"/inventory/products/{supply_id}", headers=headers).json()["current_stock"] == 5
    orders = client.get("/inventory/orders", headers=headers).json()
    assert [row["kind"] for row in orders] == ["inbound"]


def test_invalid_consumption_type_is_422() -> None:
    headers = auth_header()
    supply_id = _create_supply(headers)
    _inbound(headers, supply_id, 5)
    response = client.post(
        "/inventory/orders/outbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 1,
            "consumption_type": "theft",
            "clinic_id": 1,
        },
    )
    assert response.status_code == 422
    orders = client.get("/inventory/orders", headers=headers).json()
    assert all(row["kind"] != "outbound" for row in orders)


def test_unknown_supply_on_inbound_404() -> None:
    headers = auth_header()
    response = client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={
            "supply_id": 99999,
            "quantity": 1,
            "vendor_name": "MedLine Industries",
            "clinic_id": 1,
        },
    )
    assert response.status_code == 404


def test_clinic_and_quantity_bounds() -> None:
    headers = auth_header()
    supply_id = _create_supply(headers)
    bad_clinic = client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 1,
            "vendor_name": "MedLine Industries",
            "clinic_id": 13,
        },
    )
    bad_qty = client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 0,
            "vendor_name": "MedLine Industries",
            "clinic_id": 1,
        },
    )
    assert bad_clinic.status_code == 422
    assert bad_qty.status_code == 422


def test_orders_list_includes_both_kinds_and_supply() -> None:
    headers = auth_header()
    supply_id = _create_supply(headers)
    _inbound(headers, supply_id, 10)
    client.post(
        "/inventory/orders/outbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 2,
            "consumption_type": "clinical_use",
            "clinic_id": 1,
        },
    )
    rows = client.get("/inventory/orders", headers=headers).json()
    kinds = {row["kind"] for row in rows}
    assert kinds == {"inbound", "outbound"}
    for row in rows:
        assert row["supply"]["sku"] == "HCR-PPE-001"
        assert row["supply"]["country"] == "US"
        assert "current_stock" not in row["supply"]
