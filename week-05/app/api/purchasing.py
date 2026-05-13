"""Purchasing API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PurchaseOrder, PurchaseOrderStatus, Supplier
from app.schemas.orders import PurchaseOrderCreate, PurchaseOrderResponse
from app.services.purchase_manager import get_purchase_manager
from app.services.event_logger import EventLogger

router = APIRouter(prefix="/purchase-orders", tags=["Purchasing"])


@router.get("", response_model=List[PurchaseOrderResponse])
def list_purchase_orders(
    status: str = None,
    db: Session = Depends(get_db),
):
    """List all purchase orders, optionally filtered by status."""
    purchase_mgr = get_purchase_manager()

    if status:
        return purchase_mgr.get_purchase_orders(db, PurchaseOrderStatus(status))
    return purchase_mgr.get_purchase_orders(db)


@router.post("", response_model=dict)
def create_purchase_order(po: PurchaseOrderCreate, db: Session = Depends(get_db)):
    """
    Create a new purchase order.

    The expected_arrival is calculated automatically based on supplier lead time.
    """
    purchase_mgr = get_purchase_manager()

    result = purchase_mgr.create_purchase_order(
        db=db,
        po_id=po.id,
        supplier_id=po.supplier_id,
        material_type=po.material_type,
        quantity=po.quantity,
        order_day=po.order_day,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result["purchase_order"]


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
def get_purchase_order(po_id: str, db: Session = Depends(get_db)):
    """Get a specific purchase order."""
    purchase_mgr = get_purchase_manager()
    orders = purchase_mgr.get_purchase_orders(db)

    po = next((o for o in orders if o["id"] == po_id), None)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    return po


@router.put("/{po_id}/cancel")
def cancel_purchase_order(po_id: str, db: Session = Depends(get_db)):
    """Cancel a pending purchase order."""
    purchase_mgr = get_purchase_manager()

    # Get current day (approximation)
    from sqlalchemy import func
    from app.models import ManufacturingOrder
    current_day = db.query(func.max(ManufacturingOrder.created_day)).scalar() or 1

    result = purchase_mgr.cancel_purchase_order(db, po_id, current_day)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.get("/suppliers/{supplier_id}/products")
def get_supplier_products(supplier_id: str, db: Session = Depends(get_db)):
    """Get products available from a specific supplier."""
    purchase_mgr = get_purchase_manager()
    products = purchase_mgr.get_supplier_products(db, supplier_id)

    if not products:
        # Check if supplier exists
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    return {"supplier_id": supplier_id, "products": products}


@router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db)):
    """List all suppliers."""
    purchase_mgr = get_purchase_manager()
    suppliers = purchase_mgr.get_suppliers(db)
    return suppliers


@router.post("/estimate-cost")
def estimate_cost(
    supplier_id: str,
    material_type: str,
    quantity: float,
    db: Session = Depends(get_db),
):
    """Estimate the cost of a potential purchase order."""
    purchase_mgr = get_purchase_manager()
    result = purchase_mgr.estimate_total_cost(db, supplier_id, material_type, quantity)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error"))

    return result
