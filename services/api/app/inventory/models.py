"""SQLModel tables for inventory. current_stock is never stored."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MedicalSupply(SQLModel, table=True):
    __tablename__ = "medical_supply"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    sku: str
    category: str
    unit: str
    country: str


class SupplyDelivery(SQLModel, table=True):
    __tablename__ = "supply_delivery"

    id: int | None = Field(default=None, primary_key=True)
    supply_id: int = Field(foreign_key="medical_supply.id")
    quantity: int
    vendor_name: str
    clinic_id: int
    created_at: datetime = Field(default_factory=_utcnow)
    user_uuid: str


class SupplyConsumption(SQLModel, table=True):
    __tablename__ = "supply_consumption"

    id: int | None = Field(default=None, primary_key=True)
    supply_id: int = Field(foreign_key="medical_supply.id")
    quantity: int
    consumption_type: str
    clinic_id: int
    created_at: datetime = Field(default_factory=_utcnow)
    user_uuid: str
