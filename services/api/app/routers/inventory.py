"""Authenticated inventory catalogue and movement routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.auth.security import get_current_user
from app.cache import (
    ORDERS_LIST_KEY,
    PRODUCTS_LIST_KEY,
    invalidate_inventory_writes,
    product_item_key,
    response_cache,
)
from app.database import get_session
from app.inventory import service
from app.inventory.schemas import (
    ConsumptionCreate,
    ConsumptionPublic,
    DeliveryCreate,
    DeliveryPublic,
    MedicalSupplyCreate,
    MedicalSupplyPublic,
    OrderMovement,
)

NOT_FOUND = "Medical supply not found"

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(get_current_user)],
)


def _user_uuid(user: dict[str, Any]) -> str:
    return str(user["id"])


@router.get("/products", response_model=list[MedicalSupplyPublic])
def list_products(session: Session = Depends(get_session)) -> list[MedicalSupplyPublic]:
    cached = response_cache.get(PRODUCTS_LIST_KEY)
    if cached is not None:
        return [MedicalSupplyPublic.model_validate(row) for row in cached]
    rows = service.list_supplies(session)
    response_cache.set(
        PRODUCTS_LIST_KEY, [row.model_dump(mode="json") for row in rows]
    )
    return rows


@router.post("/products", response_model=MedicalSupplyPublic, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: MedicalSupplyCreate,
    session: Session = Depends(get_session),
) -> MedicalSupplyPublic:
    created = service.create_supply(session, payload)
    invalidate_inventory_writes(supply_id=created.id)
    return created


@router.get("/products/{supply_id}", response_model=MedicalSupplyPublic)
def get_product(
    supply_id: int, session: Session = Depends(get_session)
) -> MedicalSupplyPublic:
    key = product_item_key(supply_id)
    cached = response_cache.get(key)
    if cached is not None:
        return MedicalSupplyPublic.model_validate(cached)
    row = service.get_supply(session, supply_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    public = service.to_public(session, row)
    response_cache.set(key, public.model_dump(mode="json"))
    return public


@router.post("/orders/inbound", response_model=DeliveryPublic, status_code=status.HTTP_201_CREATED)
def create_inbound(
    payload: DeliveryCreate,
    session: Session = Depends(get_session),
    user: dict[str, Any] = Depends(get_current_user),
) -> DeliveryPublic:
    row = service.create_delivery(session, payload, _user_uuid(user))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    invalidate_inventory_writes(supply_id=payload.supply_id)
    return DeliveryPublic.model_validate(row, from_attributes=True)


@router.post("/orders/outbound", response_model=ConsumptionPublic, status_code=status.HTTP_201_CREATED)
def create_outbound(
    payload: ConsumptionCreate,
    session: Session = Depends(get_session),
    user: dict[str, Any] = Depends(get_current_user),
) -> ConsumptionPublic:
    try:
        row = service.create_consumption(session, payload, _user_uuid(user))
    except service.InsufficientStockError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    invalidate_inventory_writes(supply_id=payload.supply_id)
    return ConsumptionPublic.model_validate(row, from_attributes=True)


@router.get("/orders", response_model=list[OrderMovement])
def list_orders(session: Session = Depends(get_session)) -> list[OrderMovement]:
    cached = response_cache.get(ORDERS_LIST_KEY)
    if cached is not None:
        return [OrderMovement.model_validate(row) for row in cached]
    rows = service.list_orders(session)
    response_cache.set(ORDERS_LIST_KEY, [row.model_dump(mode="json") for row in rows])
    return rows
