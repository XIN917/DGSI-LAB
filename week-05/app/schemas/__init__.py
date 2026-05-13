"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    RELEASED = "RELEASED"
    PARTIAL = "PARTIAL"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PurchaseOrderStatus(str, Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


# Printer Model Schemas
class PrinterModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    assembly_time_hours: int = Field(..., ge=1)
    daily_capacity: int = Field(..., ge=1)


class PrinterModelCreate(PrinterModelBase):
    id: str = Field(..., min_length=1, max_length=50)


class PrinterModelResponse(PrinterModelBase):
    id: str

    class Config:
        from_attributes = True


class BOMItemBase(BaseModel):
    material_type: str = Field(..., min_length=1, max_length=50)
    quantity_per_unit: float = Field(..., gt=0)


class BOMItemCreate(BOMItemBase):
    id: str = Field(..., min_length=1, max_length=50)
    printer_model_id: str = Field(..., min_length=1, max_length=50)


class BOMItemResponse(BOMItemBase):
    id: str
    printer_model_id: str

    class Config:
        from_attributes = True


# Material Schemas
class MaterialTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    unit: str = Field(..., min_length=1, max_length=20)


class MaterialTypeCreate(MaterialTypeBase):
    id: str = Field(..., min_length=1, max_length=50)


class MaterialTypeResponse(MaterialTypeBase):
    id: str

    class Config:
        from_attributes = True


# Supplier Schemas
class SupplierProductBase(BaseModel):
    material_type: str = Field(..., min_length=1, max_length=50)
    price_per_unit: float = Field(..., gt=0)
    min_order_qty: int = Field(..., ge=1)
    packaging: Optional[str] = None


class SupplierProductCreate(SupplierProductBase):
    id: str = Field(..., min_length=1, max_length=50)
    supplier_id: str = Field(..., min_length=1, max_length=50)


class SupplierProductResponse(SupplierProductBase):
    id: str
    supplier_id: str

    class Config:
        from_attributes = True


class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    lead_time_days: int = Field(..., ge=1)


class SupplierCreate(SupplierBase):
    id: str = Field(..., min_length=1, max_length=50)


class SupplierResponse(SupplierBase):
    id: str
    products: Optional[List[SupplierProductResponse]] = None

    class Config:
        from_attributes = True


# Inventory Schemas
class InventoryLogResponse(BaseModel):
    id: str
    material_type: str
    current_quantity: float
    warehouse_capacity: int

    class Config:
        from_attributes = True


class InventoryUpdate(BaseModel):
    current_quantity: float = Field(..., ge=0)


# Manufacturing Order Schemas
class ManufacturingOrderBase(BaseModel):
    printer_model_id: str = Field(..., min_length=1, max_length=50)
    quantity: int = Field(..., ge=1)


class ManufacturingOrderCreate(ManufacturingOrderBase):
    id: str = Field(..., min_length=1, max_length=50)
    created_day: int = Field(..., ge=1)


class ManufacturingOrderResponse(ManufacturingOrderBase):
    id: str
    status: OrderStatus
    created_day: int
    released_day: Optional[int] = None
    completed_day: Optional[int] = None

    class Config:
        from_attributes = True


class ManufacturingOrderRelease(BaseModel):
    released_day: int = Field(..., ge=1)


# Purchase Order Schemas
class PurchaseOrderBase(BaseModel):
    supplier_id: str = Field(..., min_length=1, max_length=50)
    material_type: str = Field(..., min_length=1, max_length=50)
    quantity: float = Field(..., gt=0)


class PurchaseOrderCreate(PurchaseOrderBase):
    id: str = Field(..., min_length=1, max_length=50)
    order_day: int = Field(..., ge=1)
    expected_arrival: int = Field(..., ge=1)


class PurchaseOrderResponse(PurchaseOrderBase):
    id: str
    order_day: int
    expected_arrival: int
    actual_arrival: Optional[int] = None
    status: PurchaseOrderStatus

    class Config:
        from_attributes = True


# Event Log Schemas
class EventLogResponse(BaseModel):
    id: str
    day: int
    timestamp: float
    event_type: str
    category: str
    description: str
    details: Optional[str] = None

    class Config:
        from_attributes = True


class EventLogCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    day: int = Field(..., ge=1)
    timestamp: float = Field(..., ge=0)
    event_type: str = Field(..., min_length=1, max_length=50)
    category: str = Field(..., min_length=1, max_length=20)
    description: str = Field(..., min_length=1)
    details: Optional[str] = None


# Simulation Status
class SimulationStatusResponse(BaseModel):
    current_day: int
    running: bool


# Export/Import Schemas
class ExportState(BaseModel):
    inventory: List[InventoryLogResponse]
    purchase_orders: List[PurchaseOrderResponse]
    manufacturing_orders: List[ManufacturingOrderResponse]
    events: List[EventLogResponse]
    current_day: int


class ImportState(ExportState):
    pass
