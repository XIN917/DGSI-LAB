"""Purchase Order API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.purchase_order_service import PurchaseOrderService

router = APIRouter(prefix="/api/purchase-orders", tags=["purchase-orders"])


class CreatePORequest(BaseModel):
    supplier_id: int
    product_name: str
    quantity: float


class POResponse(BaseModel):
    id: int
    supplier_id: int
    supplier_name: Optional[str] = None
    product_name: str
    quantity_ordered: float
    quantity_delivered: float
    unit_cost: float
    total_cost: float
    order_date: str
    expected_delivery: str
    actual_delivery: Optional[str] = None
    status: str


@router.get("", response_model=List[POResponse])
def list_purchase_orders(db: Session = Depends(get_db)):
    """List all purchase orders."""
    return PurchaseOrderService(db).list()


@router.get("/{po_id}", response_model=POResponse)
def get_purchase_order(po_id: int, db: Session = Depends(get_db)):
    """Get purchase order details."""
    result = PurchaseOrderService(db).get(po_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Purchase order #{po_id} not found")
    return result


@router.post("", response_model=POResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_order(body: CreatePORequest, db: Session = Depends(get_db)):
    """Create a purchase order. Applies bulk discount tiers automatically."""
    try:
        return PurchaseOrderService(db).create(body.supplier_id, body.product_name, body.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{po_id}/cancel")
def cancel_purchase_order(po_id: int, db: Session = Depends(get_db)):
    """Cancel a pending purchase order."""
    try:
        return PurchaseOrderService(db).cancel(po_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
