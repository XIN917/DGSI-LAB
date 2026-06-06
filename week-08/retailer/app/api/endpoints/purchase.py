from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from app.models.order import PurchaseOrder
from app.services.retailer_service import RetailerService
from app.core.database import get_db

router = APIRouter()


@router.get("", response_model=List[PurchaseOrder])
def list_purchase_orders(db: Session = Depends(get_db)):
    """List all purchase orders placed with manufacturer."""
    service = RetailerService(db)
    return service.list_purchase_orders()


@router.post("", response_model=dict)
def create_purchase_order(sku: str, quantity: int, db: Session = Depends(get_db)):
    """Create a new purchase order to the manufacturer."""
    service = RetailerService(db)
    try:
        return service.create_purchase_order(sku, quantity)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{po_id}/sync", response_model=dict)
def sync_purchase_order(po_id: int, db: Session = Depends(get_db)):
    """Sync purchase order status with the manufacturer."""
    service = RetailerService(db)
    try:
        return service.sync_purchase_order(po_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
