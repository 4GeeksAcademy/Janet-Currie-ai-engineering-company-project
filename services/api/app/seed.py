"""Seed TinyDB with HealthCore supplier directory data.

Run from services/api:
  uv run seed
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.suppliers.db import VALID_CATEGORIES, close_db, suppliers_table
from app.suppliers.models import SupplierCreate
from app.suppliers.seed_data import SUPPLIERS_SEED

VOLUME_EXTRA_SUPPLIERS = 40


def seed_suppliers(*, reset: bool = True) -> int:
    table = suppliers_table()
    if reset:
        table.truncate()

    now = datetime.now(timezone.utc)
    existing = {doc.get("name") for doc in table}
    count = 0
    for raw in SUPPLIERS_SEED:
        payload = SupplierCreate.model_validate(raw)
        if payload.name in existing:
            continue
        doc = payload.model_dump(mode="json")
        doc["updated_at"] = now.isoformat()
        table.insert(doc)
        existing.add(payload.name)
        count += 1
    return count


def seed_suppliers_volume(extra: int = VOLUME_EXTRA_SUPPLIERS) -> int:
    """Insert extra synthetic suppliers by unique name; skip names already present."""
    table = suppliers_table()
    existing = {doc.get("name") for doc in table}
    now = datetime.now(timezone.utc)
    added = 0
    for index in range(extra):
        name = f"Load Test Supplier {index:03d}"
        if name in existing:
            continue
        country = "USA" if index % 2 == 0 else "UK"
        payload = SupplierCreate.model_validate(
            {
                "name": name,
                "country": country,
                "categories": [VALID_CATEGORIES[index % len(VALID_CATEGORIES)]],
                "monthly_rate": 10 + (index % 50),
                "currency": "USD" if country == "USA" else "GBP",
                "status": "active" if index % 5 else "suspended",
                "compliance_agreement": "BAA" if country == "USA" else "DPA",
                "notes": None,
            }
        )
        doc = payload.model_dump(mode="json")
        doc["updated_at"] = now.isoformat()
        table.insert(doc)
        existing.add(name)
        added += 1
    return added


def main() -> None:
    import os

    try:
        count = seed_suppliers(reset=True)
        extra = int(os.getenv("SUPPLIER_LOAD_EXTRA", "0"))
        added = seed_suppliers_volume(extra=extra) if extra else 0
        print(f"Seeded {count} suppliers into TinyDB.")
        if extra:
            print(f"Volume extras: +{added} suppliers.")
    finally:
        close_db()


if __name__ == "__main__":
    main()
