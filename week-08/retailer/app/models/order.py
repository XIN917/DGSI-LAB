from datetime import date
from enum import Enum
from pydantic import BaseModel


class OrderStatus(str, Enum):
    pending = "pending"
    fulfilled = "fulfilled"
    backordered = "backordered"
    cancelled = "cancelled"


class CustomerOrder(BaseModel):
    id: int
    sku: str
    quantity: int
    retail_price: float
    status: OrderStatus
    created_day: int
    fulfilled_day: int | None = None
    customer_name: str | None = None
    notes: str | None = None


class PurchaseOrder(BaseModel):
    id: int
    manufacturer_po_id: int | None = None
    sku: str
    quantity: int
    wholesale_unit_price: float
    status: str
    placed_day: int
    expected_delivery_day: int | None = None
    received_day: int | None = None
