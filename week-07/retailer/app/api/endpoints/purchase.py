from fastapi import APIRouter, HTTPException
from typing import List

from app.models.order import PurchaseOrder
from app.services.retailer_service import RetailerService

router = APIRouter()
service = RetailerService()


@router.get("/", response_model=List[PurchaseOrder])
async def list_purchase_orders():
    """List all purchase orders placed with manufacturer."""
    return await service.list_purchase_orders()


@router.post("/", response_model=dict)
async def create_purchase_order(sku: str, quantity: int):
    """Create a new purchase order to the manufacturer."""
    try:
        return await service.create_purchase_order(sku, quantity)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{po_id}/sync", response_model=dict)
async def sync_purchase_order(po_id: int):
    """Sync purchase order status with the manufacturer."""
    try:
        return await service.sync_purchase_order(po_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
