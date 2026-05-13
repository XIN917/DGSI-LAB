"""Orders API schema definitions."""

from pydantic import BaseModel, Field
from typing import Optional, List
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


# BOM Schemas
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
    completed_quantity: int
    created_day: int
    released_day: Optional[int] = None
    completed_day: Optional[int] = None

    class Config:
        from_attributes = True


class ManufacturingOrderRelease(BaseModel):
    released_day: int = Field(..., ge=1)


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
