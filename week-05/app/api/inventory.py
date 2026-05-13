"""Inventory API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import InventoryLog, MaterialType
from app.schemas.inventory import InventoryLogResponse, InventoryUpdate
from app.services.inventory_manager import get_inventory_manager

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=List[InventoryLogResponse])
def get_inventory(db: Session = Depends(get_db)):
    """Get current inventory levels for all materials."""
    inventory_mgr = get_inventory_manager()
    items = inventory_mgr.get_inventory_levels(db)
    return items


@router.get("/capacity")
def get_warehouse_capacity(db: Session = Depends(get_db)):
    """Get warehouse capacity information."""
    inventory_mgr = get_inventory_manager()
    return inventory_mgr.check_warehouse_capacity(db)


@router.get("/{material_type}", response_model=InventoryLogResponse)
def get_material_inventory(material_type: str, db: Session = Depends(get_db)):
    """Get inventory level for a specific material."""
    inventory_mgr = get_inventory_manager()
    item = inventory_mgr.get_material_stock(db, material_type)

    if not item:
        # Create if doesn't exist
        from app.schemas.inventory import InventoryLogCreate
        # Find or create material type first
        mat = db.query(MaterialType).filter(MaterialType.id == material_type).first()
        if not mat:
            raise HTTPException(status_code=404, detail="Material type not found")

        new_item = InventoryLog(id=f"inv_{material_type}", material_type=material_type, current_quantity=0.0)
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item

    # Return as InventoryLogResponse-like dict
    return item


@router.post("/{material_type}/adjust")
def adjust_inventory(material_type: str, update: InventoryUpdate, db: Session = Depends(get_db)):
    """Adjust inventory level for a material (used internally by simulation)."""
    inventory_mgr = get_inventory_manager()

    # Calculate change
    item = db.query(InventoryLog).filter(InventoryLog.material_type == material_type).first()
    if not item:
        raise HTTPException(status_code=404, detail="Material not found in inventory")

    change = update.current_quantity - item.current_quantity
    result = inventory_mgr.update_stock(db, material_type, change, 1)  # Day 1 for manual adjustments

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    db.refresh(item)
    return item
