"""Seed local inventory rows. Requires a TinyDB user (run seed-auth first)."""

from __future__ import annotations

from sqlmodel import Session, select

from app.auth.models import Role
from app.auth.security import hash_password
from app.auth.service import create_user, list_users
from app.database import get_engine, init_db
from app.inventory.models import MedicalSupply, SupplyConsumption, SupplyDelivery

SUPPLIES = [
    {
        "name": "Nitrile gloves (box of 100)",
        "sku": "HCR-PPE-001",
        "category": "ppe",
        "unit": "box",
        "country": "US",
    },
    {
        "name": "Surgical mask (pack of 50)",
        "sku": "HCR-PPE-002",
        "category": "ppe",
        "unit": "pack",
        "country": "UK",
    },
    {
        "name": "Adhesive wound dressing",
        "sku": "HCR-WND-001",
        "category": "wound_care",
        "unit": "box",
        "country": "US",
    },
    {
        "name": "Rapid strep test kit",
        "sku": "HCR-DIAG-001",
        "category": "diagnostics",
        "unit": "unit",
        "country": "US",
    },
    {
        "name": "Blood glucose test strips (50)",
        "sku": "HCR-DIAG-002",
        "category": "diagnostics",
        "unit": "box",
        "country": "UK",
    },
    {
        "name": "0.9% Saline solution 500ml",
        "sku": "HCR-MED-001",
        "category": "medications",
        "unit": "vial",
        "country": "US",
    },
]


def _tiny_user_uuid() -> str:
    users = list_users()
    if users:
        return str(users[0]["id"])
    created = create_user(
        email="admin@healthcore.example",
        hashed_password=hash_password("HealthCore!dev-admin"),
        role=Role.admin,
        name="Local Admin",
    )
    return str(created["id"])


def seed_inventory(session: Session, user_uuid: str, *, reset: bool = True) -> dict[str, int]:
    if reset:
        for row in session.exec(select(SupplyConsumption)).all():
            session.delete(row)
        for row in session.exec(select(SupplyDelivery)).all():
            session.delete(row)
        for row in session.exec(select(MedicalSupply)).all():
            session.delete(row)
        session.commit()

    supplies: dict[str, MedicalSupply] = {}
    for payload in SUPPLIES:
        row = MedicalSupply(**payload)
        session.add(row)
        session.flush()
        supplies[row.sku] = row

    gloves = supplies["HCR-PPE-001"]
    masks = supplies["HCR-PPE-002"]
    dressing = supplies["HCR-WND-001"]

    deliveries = [
        SupplyDelivery(
            supply_id=gloves.id,
            quantity=100,
            vendor_name="MedLine Industries",
            clinic_id=1,
            user_uuid=user_uuid,
        ),
        SupplyDelivery(
            supply_id=gloves.id,
            quantity=40,
            vendor_name="Bound Tree Medical",
            clinic_id=3,
            user_uuid=user_uuid,
        ),
        SupplyDelivery(
            supply_id=masks.id,
            quantity=20,
            vendor_name="Cardinal Health UK",
            clinic_id=10,
            user_uuid=user_uuid,
        ),
        SupplyDelivery(
            supply_id=dressing.id,
            quantity=15,
            vendor_name="MedLine Industries",
            clinic_id=2,
            user_uuid=user_uuid,
        ),
    ]
    consumptions = [
        SupplyConsumption(
            supply_id=gloves.id,
            quantity=25,
            consumption_type="clinical_use",
            clinic_id=1,
            user_uuid=user_uuid,
        ),
        SupplyConsumption(
            supply_id=gloves.id,
            quantity=10,
            consumption_type="expiry_waste",
            clinic_id=3,
            user_uuid=user_uuid,
        ),
        SupplyConsumption(
            supply_id=masks.id,
            quantity=5,
            consumption_type="clinical_use",
            clinic_id=10,
            user_uuid=user_uuid,
        ),
    ]
    for row in deliveries:
        session.add(row)
    for row in consumptions:
        session.add(row)
    session.commit()
    return {
        "supplies": len(SUPPLIES),
        "deliveries": len(deliveries),
        "consumptions": len(consumptions),
    }


def main() -> None:
    from app.auth.db import close_db

    try:
        user_uuid = _tiny_user_uuid()
        init_db()
        with Session(get_engine()) as session:
            counts = seed_inventory(session, user_uuid, reset=True)
        print(
            "Seeded inventory: "
            f"{counts['supplies']} supplies, {counts['deliveries']} deliveries, "
            f"{counts['consumptions']} consumptions (user_uuid={user_uuid}). "
            "HCR-PPE-001 stock should be 105 (100+40-25-10)."
        )
    finally:
        close_db()


if __name__ == "__main__":
    main()
