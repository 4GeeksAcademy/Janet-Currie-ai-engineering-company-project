"""GET/POST /inventory/products — computed stock and catalogue rules."""

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


def test_create_product_requires_auth() -> None:
    assert client.post("/inventory/products", json=GLOVES).status_code == 401


def test_create_product_returns_zero_stock() -> None:
    headers = auth_header()
    response = client.post("/inventory/products", headers=headers, json=GLOVES)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == GLOVES["name"]
    assert body["sku"] == GLOVES["sku"]
    assert body["country"] == "US"
    assert body["current_stock"] == 0
    assert "id" in body


def test_client_cannot_set_current_stock() -> None:
    headers = auth_header()
    payload = {**GLOVES, "current_stock": 999}
    body = client.post("/inventory/products", headers=headers, json=payload).json()
    assert body["current_stock"] == 0


def test_list_and_get_include_computed_stock() -> None:
    headers = auth_header()
    created = client.post("/inventory/products", headers=headers, json=GLOVES).json()
    supply_id = created["id"]
    client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 10,
            "vendor_name": "MedLine Industries",
            "clinic_id": 1,
        },
    )
    client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 5,
            "vendor_name": "Bound Tree Medical",
            "clinic_id": 2,
        },
    )
    listed = client.get("/inventory/products", headers=headers).json()
    assert listed[0]["current_stock"] == 15
    single = client.get(f"/inventory/products/{supply_id}", headers=headers).json()
    assert single["current_stock"] == 15
    assert single["country"] == "US"


def test_unknown_product_404() -> None:
    headers = auth_header()
    response = client.get("/inventory/products/99999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Medical supply not found"


def test_country_must_be_us_or_uk() -> None:
    headers = auth_header()
    payload = {**GLOVES, "country": "USA"}
    response = client.post("/inventory/products", headers=headers, json=payload)
    assert response.status_code == 422
