"""Request/response schemas. current_stock is response-only."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SupplyCategory = Literal[
    "ppe", "wound_care", "diagnostics", "medications", "consumables"
]
Country = Literal["US", "UK"]
ConsumptionType = Literal["clinical_use", "expiry_waste"]
OrderKind = Literal["inbound", "outbound"]


class MedicalSupplyCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    category: SupplyCategory
    unit: str = Field(min_length=1)
    country: Country


class MedicalSupplyPublic(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    unit: str
    country: str
    current_stock: int


class SupplySummary(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    unit: str
    country: str


class DeliveryCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    supply_id: int
    quantity: int = Field(gt=0)
    vendor_name: str = Field(min_length=1)
    clinic_id: int = Field(ge=1, le=12)


class ConsumptionCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    supply_id: int
    quantity: int = Field(gt=0)
    consumption_type: ConsumptionType
    clinic_id: int = Field(ge=1, le=12)


class DeliveryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supply_id: int
    quantity: int
    vendor_name: str
    clinic_id: int
    created_at: datetime
    user_uuid: str


class ConsumptionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supply_id: int
    quantity: int
    consumption_type: str
    clinic_id: int
    created_at: datetime
    user_uuid: str


class OrderMovement(BaseModel):
    kind: OrderKind
    id: int
    supply_id: int
    quantity: int
    clinic_id: int
    created_at: datetime
    user_uuid: str
    vendor_name: str | None = None
    consumption_type: str | None = None
    supply: SupplySummary
