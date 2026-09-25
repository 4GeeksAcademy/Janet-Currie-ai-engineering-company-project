"""TTL cache behavior for inventory catalogue and movements."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.cache import INVENTORY_TTL_SECONDS, response_cache
from app.inventory import service
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
    response_cache.clear()
    response_cache.set_clock(__import__("time").monotonic)
    yield
    response_cache.clear()
    response_cache.set_clock(__import__("time").monotonic)


class FakeClock:
    def __init__(self, start: float = 1_000.0) -> None:
        self.value = start

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def _create_supply(headers: dict) -> int:
    return client.post("/inventory/products", headers=headers, json=GLOVES).json()["id"]


def test_unauthenticated_get_is_not_cached() -> None:
    assert client.get("/inventory/products").status_code == 401
    assert len(response_cache) == 0


def test_list_products_miss_then_hit_skips_service() -> None:
    headers = auth_header()
    _create_supply(headers)
    with patch(
        "app.routers.inventory.service.list_supplies", wraps=service.list_supplies
    ) as spy:
        first = client.get("/inventory/products", headers=headers)
        second = client.get("/inventory/products", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()[0]["sku"] == GLOVES["sku"]
    assert "hashed_password" not in first.json()[0]
    assert spy.call_count == 1


def test_product_detail_and_list_keys_do_not_collide() -> None:
    headers = auth_header()
    supply_id = _create_supply(headers)
    listed = client.get("/inventory/products", headers=headers).json()
    detail = client.get(f"/inventory/products/{supply_id}", headers=headers).json()
    assert listed[0]["id"] == detail["id"]
    assert listed[0]["current_stock"] == detail["current_stock"] == 0


def test_unknown_product_404_is_not_cached() -> None:
    headers = auth_header()
    assert client.get("/inventory/products/99999", headers=headers).status_code == 404
    assert len(response_cache) == 0


def test_ttl_expiry_recomputes() -> None:
    headers = auth_header()
    _create_supply(headers)
    clock = FakeClock()
    response_cache.set_clock(clock)
    with patch(
        "app.routers.inventory.service.list_supplies", wraps=service.list_supplies
    ) as spy:
        assert client.get("/inventory/products", headers=headers).status_code == 200
        clock.advance(INVENTORY_TTL_SECONDS + 0.1)
        assert client.get("/inventory/products", headers=headers).status_code == 200
    assert spy.call_count == 2


def test_successful_inbound_invalidates_products_and_orders() -> None:
    headers = auth_header()
    supply_id = _create_supply(headers)
    with patch(
        "app.routers.inventory.service.list_supplies", wraps=service.list_supplies
    ) as products_spy:
        with patch(
            "app.routers.inventory.service.list_orders", wraps=service.list_orders
        ) as orders_spy:
            client.get("/inventory/products", headers=headers)
            client.get("/inventory/orders", headers=headers)
            inbound = client.post(
                "/inventory/orders/inbound",
                headers=headers,
                json={
                    "supply_id": supply_id,
                    "quantity": 8,
                    "vendor_name": "MedLine Industries",
                    "clinic_id": 1,
                },
            )
            assert inbound.status_code == 201
            after_products = client.get("/inventory/products", headers=headers)
            after_orders = client.get("/inventory/orders", headers=headers)
    assert after_products.json()[0]["current_stock"] == 8
    assert after_orders.json()[0]["quantity"] == 8
    assert products_spy.call_count == 2
    assert orders_spy.call_count == 2


def test_failed_outbound_does_not_invalidate() -> None:
    headers = auth_header()
    supply_id = _create_supply(headers)
    client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 5,
            "vendor_name": "MedLine Industries",
            "clinic_id": 1,
        },
    )
    with patch(
        "app.routers.inventory.service.list_supplies", wraps=service.list_supplies
    ) as spy:
        first = client.get("/inventory/products", headers=headers)
        failed = client.post(
            "/inventory/orders/outbound",
            headers=headers,
            json={
                "supply_id": supply_id,
                "quantity": 99,
                "consumption_type": "clinical_use",
                "clinic_id": 1,
            },
        )
        second = client.get("/inventory/products", headers=headers)
    assert failed.status_code == 400
    assert first.json() == second.json()
    assert first.json()[0]["current_stock"] == 5
    assert spy.call_count == 1


def test_cached_orders_match_uncached_schema() -> None:
    headers = auth_header()
    supply_id = _create_supply(headers)
    client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={
            "supply_id": supply_id,
            "quantity": 2,
            "vendor_name": "MedLine Industries",
            "clinic_id": 4,
        },
    )
    first = client.get("/inventory/orders", headers=headers)
    second = client.get("/inventory/orders", headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    row = first.json()[0]
    assert row["kind"] == "inbound"
    assert "supply" in row
    assert row["supply"]["sku"] == GLOVES["sku"]
    assert "hashed_password" not in row
