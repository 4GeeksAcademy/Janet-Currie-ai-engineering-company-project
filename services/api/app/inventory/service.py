"""Inventory business rules: computed stock and no-negative-stock outbound."""

from __future__ import annotations

from sqlmodel import Session, col, select

from app.inventory.models import MedicalSupply, SupplyConsumption, SupplyDelivery
from app.inventory.schemas import (
    ConsumptionCreate,
    DeliveryCreate,
    MedicalSupplyCreate,
    MedicalSupplyPublic,
    OrderMovement,
    SupplySummary,
)


class InsufficientStockError(Exception):
    def __init__(self, name: str, available: int, quantity: int) -> None:
        self.name = name
        self.available = available
        self.quantity = quantity
        super().__init__(
            f"Insufficient stock for supply '{name}'. Available: {available}, requested: {quantity}."
        )

    @property
    def detail(self) -> str:
        return (
            f"Insufficient stock for supply '{self.name}'. "
            f"Available: {self.available}, requested: {self.quantity}."
        )


def current_stock(session: Session, supply_id: int) -> int:
    inbound = session.exec(
        select(SupplyDelivery.quantity).where(SupplyDelivery.supply_id == supply_id)
    ).all()
    outbound = session.exec(
        select(SupplyConsumption.quantity).where(SupplyConsumption.supply_id == supply_id)
    ).all()
    return sum(inbound) - sum(outbound)


def to_public(session: Session, supply: MedicalSupply) -> MedicalSupplyPublic:
    assert supply.id is not None
    return MedicalSupplyPublic(
        id=supply.id,
        name=supply.name,
        sku=supply.sku,
        category=supply.category,
        unit=supply.unit,
        country=supply.country,
        current_stock=current_stock(session, supply.id),
    )


def to_summary(supply: MedicalSupply) -> SupplySummary:
    assert supply.id is not None
    return SupplySummary(
        id=supply.id,
        name=supply.name,
        sku=supply.sku,
        category=supply.category,
        unit=supply.unit,
        country=supply.country,
    )


def get_supply(session: Session, supply_id: int) -> MedicalSupply | None:
    return session.get(MedicalSupply, supply_id)


def list_supplies(session: Session) -> list[MedicalSupplyPublic]:
    rows = session.exec(select(MedicalSupply).order_by(col(MedicalSupply.id))).all()
    return [to_public(session, row) for row in rows]


def create_supply(session: Session, payload: MedicalSupplyCreate) -> MedicalSupplyPublic:
    row = MedicalSupply(**payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return to_public(session, row)


def create_delivery(
    session: Session, payload: DeliveryCreate, user_uuid: str
) -> SupplyDelivery | None:
    supply = get_supply(session, payload.supply_id)
    if supply is None:
        return None
    row = SupplyDelivery(
        supply_id=payload.supply_id,
        quantity=payload.quantity,
        vendor_name=payload.vendor_name,
        clinic_id=payload.clinic_id,
        user_uuid=user_uuid,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_consumption(
    session: Session, payload: ConsumptionCreate, user_uuid: str
) -> SupplyConsumption | None:
    dialect = session.get_bind().dialect.name
    query = select(MedicalSupply).where(MedicalSupply.id == payload.supply_id)
    if dialect != "sqlite":
        query = query.with_for_update()
    supply = session.exec(query).first()
    if supply is None:
        return None
    assert supply.id is not None
    available = current_stock(session, supply.id)
    if payload.quantity > available:
        raise InsufficientStockError(supply.name, available, payload.quantity)
    row = SupplyConsumption(
        supply_id=payload.supply_id,
        quantity=payload.quantity,
        consumption_type=payload.consumption_type,
        clinic_id=payload.clinic_id,
        user_uuid=user_uuid,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_orders(session: Session) -> list[OrderMovement]:
    supplies = {row.id: row for row in session.exec(select(MedicalSupply)).all()}
    movements: list[OrderMovement] = []
    for row in session.exec(select(SupplyDelivery)).all():
        supply = supplies.get(row.supply_id)
        if supply is None or row.id is None:
            continue
        movements.append(
            OrderMovement(
                kind="inbound",
                id=row.id,
                supply_id=row.supply_id,
                quantity=row.quantity,
                clinic_id=row.clinic_id,
                created_at=row.created_at,
                user_uuid=row.user_uuid,
                vendor_name=row.vendor_name,
                supply=to_summary(supply),
            )
        )
    for row in session.exec(select(SupplyConsumption)).all():
        supply = supplies.get(row.supply_id)
        if supply is None or row.id is None:
            continue
        movements.append(
            OrderMovement(
                kind="outbound",
                id=row.id,
                supply_id=row.supply_id,
                quantity=row.quantity,
                clinic_id=row.clinic_id,
                created_at=row.created_at,
                user_uuid=row.user_uuid,
                consumption_type=row.consumption_type,
                supply=to_summary(supply),
            )
        )
    movements.sort(key=lambda item: item.created_at, reverse=True)
    return movements
