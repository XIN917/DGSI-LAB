"""Orders API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.models import ManufacturingOrder, OrderStatus, PrinterModel, BOMItem, EventLog
from app.schemas.orders import (
    ManufacturingOrderCreate,
    ManufacturingOrderResponse,
    ManufacturingOrderRelease,
)
from app.services.order_manager import get_order_manager
from app.services.event_logger import EventLogger

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=List[ManufacturingOrderResponse])
def list_orders(
    status: str = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
):
    """List all manufacturing orders, optionally filtered by status."""
    query = db.query(ManufacturingOrder)
    if status:
        query = query.filter(ManufacturingOrder.status == OrderStatus(status))
    return query.all()


@router.post("", response_model=ManufacturingOrderResponse)
def create_order(order: ManufacturingOrderCreate, db: Session = Depends(get_db)):
    """Create a new manufacturing order."""
    # Verify printer model exists
    model = db.query(PrinterModel).filter(PrinterModel.id == order.printer_model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Printer model not found")

    db_order = ManufacturingOrder(**order.model_dump())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Log event
    EventLogger.log_order_created(
        db, order.created_day, db_order.id, order.printer_model_id, order.quantity
    )

    return db_order


@router.get("/{order_id}", response_model=ManufacturingOrderResponse)
def get_order(order_id: str, db: Session = Depends(get_db)):
    """Get a specific order with BOM breakdown."""
    order = db.query(ManufacturingOrder).filter(ManufacturingOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/{order_id}/release", response_model=dict)
def release_order(order_id: str, release_data: ManufacturingOrderRelease, db: Session = Depends(get_db)):
    """Release an order to production (with material check and consumption)."""
    order_mgr = get_order_manager()

    result = order_mgr.release_order(db, order_id, release_data.released_day)

    if not result["success"]:
        error_info = result.get("error", {})
        if "shortages" in error_info:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Insufficient materials",
                    "shortages": error_info["shortages"],
                }
            )
        raise HTTPException(status_code=400, detail=error_info.get("error", "Cannot release order"))

    return {
        "success": True,
        "order_id": order_id,
        "status": result["status"],
        "consumed_materials": result.get("consumed_materials", []),
    }


@router.put("/{order_id}/cancel", response_model=dict)
def cancel_order(order_id: str, db: Session = Depends(get_db)):
    """Cancel a pending order."""
    order_mgr = get_order_manager()

    # Get current day from context (use max created_day + 1 as approximation)
    current_day = db.query(func.max(ManufacturingOrder.created_day)).scalar() or 1

    result = order_mgr.cancel_order(db, order_id, current_day)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Cannot cancel order"))

    return result


@router.get("/{order_id}/bom-breakdown", response_model=dict)
def get_order_bom_breakdown(order_id: str, db: Session = Depends(get_db)):
    """Get BOM breakdown for an order showing required materials."""
    order = db.query(ManufacturingOrder).filter(ManufacturingOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    bom_items = db.query(BOMItem).filter(BOMItem.printer_model_id == order.printer_model_id).all()
    breakdown = [
        {
            "material_type": item.material_type,
            "quantity_per_unit": item.quantity_per_unit,
            "total_required": item.quantity_per_unit * order.quantity,
        }
        for item in bom_items
    ]

    return {
        "order_id": order_id,
        "printer_model": order.printer_model_id,
        "quantity": order.quantity,
        "bom_breakdown": breakdown,
    }


@router.get("/{order_id}/check-release", response_model=dict)
def check_order_release(order_id: str, db: Session = Depends(get_db)):
    """Check if an order can be released (material availability check)."""
    order_mgr = get_order_manager()

    can_release, error_info = order_mgr.can_release_order(db, order_id)

    if not can_release:
        return {
            "can_release": False,
            "reason": error_info.get("error"),
            "shortages": error_info.get("shortages", {}),
        }

    return {
        "can_release": True,
        "order_id": order_id,
    }
