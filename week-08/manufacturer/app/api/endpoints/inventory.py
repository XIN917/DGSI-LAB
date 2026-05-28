"""Inventory API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from decimal import Decimal

from app.core.database import get_db
from app.core.config import get_settings
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/inventory", tags=["inventory"])
settings = get_settings()


class InventoryItemResponse(BaseModel):
    product_name: str
    quantity: float
    reserved_quantity: float
    available: float
    max_capacity: float
    unit_type: str


class WarehouseUsageResponse(BaseModel):
    items: List[InventoryItemResponse]
    total_units: float
    capacity: int
    usage_pct: float


class AdjustRequest(BaseModel):
    product_name: str
    new_quantity: float
    reason: str | None = None


@router.get("", response_model=WarehouseUsageResponse)
def get_inventory(db: Session = Depends(get_db)):
    """Get all inventory levels with warehouse capacity usage."""
    svc = InventoryService(db)
    items = svc.get_all()
    usage = svc.get_warehouse_usage(settings.DEFAULT_WAREHOUSE_CAPACITY)
    return {
        "items": [_serialize(i) for i in items],
        "total_units": usage["used"],
        "capacity": usage["capacity"],
        "usage_pct": round(usage["percentage"], 1),
    }


@router.get("/{product_name}", response_model=InventoryItemResponse)
def get_inventory_item(product_name: str, db: Session = Depends(get_db)):
    """Get inventory level for a specific product."""
    svc = InventoryService(db)
    item = svc.get_by_product(product_name)
    if not item:
        raise HTTPException(status_code=404, detail=f"Product '{product_name}' not found in inventory")
    return _serialize(item)


@router.post("/adjust", response_model=InventoryItemResponse)
def adjust_inventory(body: AdjustRequest, db: Session = Depends(get_db)):
    """Manually adjust inventory quantity and log the action."""
    svc = InventoryService(db)
    updated = svc.adjust_and_log(
        body.product_name,
        Decimal(str(body.new_quantity)),
        body.reason or "Manual adjustment",
    )
    return _serialize(updated)


def _serialize(item) -> dict:
    return {
        "product_name": item.product_name,
        "quantity": float(item.quantity),
        "reserved_quantity": float(item.reserved_quantity),
        "available": float(item.quantity - item.reserved_quantity),
        "max_capacity": float(getattr(item, "max_capacity", 250)),
        "unit_type": item.unit_type or "raw",
    }
