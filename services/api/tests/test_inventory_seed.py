"""Seed dataset counts and nonnegative glove stock."""

from __future__ import annotations

import pytest
from sqlmodel import Session, select

from app.database import get_engine
from app.inventory.models import MedicalSupply, SupplyConsumption, SupplyDelivery
from app.inventory.seed import seed_inventory
from app.inventory.service import current_stock
from tests.helpers import auth_header, client, reset_inventory_db


@pytest.fixture(autouse=True)
def _reset_inventory() -> None:
    reset_inventory_db()


def test_seed_meets_required_counts_and_glove_balance() -> None:
    headers = auth_header()
    with Session(get_engine()) as session:
        counts = seed_inventory(session, user_uuid="1", reset=True)
    assert counts["supplies"] == 6
    assert counts["deliveries"] == 4
    assert counts["consumptions"] == 3

    with Session(get_engine()) as session:
        supplies = session.exec(select(MedicalSupply)).all()
        deliveries = session.exec(select(SupplyDelivery)).all()
        consumptions = session.exec(select(SupplyConsumption)).all()
        gloves = next(row for row in supplies if row.sku == "HCR-PPE-001")
        glove_deliveries = [row for row in deliveries if row.supply_id == gloves.id]
        types = {row.consumption_type for row in consumptions}
        assert len(glove_deliveries) >= 2
        assert {row.quantity for row in glove_deliveries} == {100, 40}
        assert types == {"clinical_use", "expiry_waste"}
        assert current_stock(session, gloves.id) == 105
        assert current_stock(session, gloves.id) >= 0

    listed = client.get("/inventory/products", headers=headers).json()
    gloves_api = next(row for row in listed if row["sku"] == "HCR-PPE-001")
    assert gloves_api["current_stock"] == 105
    assert gloves_api["country"] == "US"


def test_volume_seed_is_idempotent() -> None:
    from app.inventory.seed import seed_inventory_volume

    with Session(get_engine()) as session:
        seed_inventory(session, user_uuid="1", reset=True)
        first = seed_inventory_volume(session, user_uuid="1", extra_count=5)
        second = seed_inventory_volume(session, user_uuid="1", extra_count=5)
    assert first["extra_supplies"] == 5
    assert second["extra_supplies"] == 0
    assert first["total_supplies"] == second["total_supplies"] == 11
