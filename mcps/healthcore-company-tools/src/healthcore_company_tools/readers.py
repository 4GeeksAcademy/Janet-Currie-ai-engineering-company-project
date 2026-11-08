"""Adapters over the existing incident store and inventory reads.

The door does not keep its own tables. Tests replace these functions.
A separate door process can see inventory only when it shares the API
database. Incident rows stay in the API process memory, so a second
process does not see an upload made in the API process.
"""

from __future__ import annotations


def fetch_incident(incident_id: str) -> dict | None:
    from app.store import get_incident

    return get_incident(incident_id)


def fetch_inventory(product_id: int | None) -> list[dict] | None:
    from app.database import get_session
    from app.inventory.service import get_supply, list_supplies, to_public

    session_gen = get_session()
    session = next(session_gen)
    try:
        if product_id is None:
            return [item.model_dump() for item in list_supplies(session)]
        supply = get_supply(session, product_id)
        if supply is None:
            return None
        return [to_public(session, supply).model_dump()]
    finally:
        session_gen.close()


def create_supply(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError("inventory writes are not available on this door")


def create_delivery(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError("inventory writes are not available on this door")


def create_consumption(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError("inventory writes are not available on this door")
