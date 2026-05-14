from fastapi import APIRouter, HTTPException
from typing import List
from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.models.database import PurchaseOrderDB
from app.models.order import PurchaseOrder
from app.services.retailer_service import RetailerService

router = APIRouter()
service = RetailerService()


@router.get("/", response_model=List[PurchaseOrder])
async def list_purchase_orders():
    """List all purchase orders placed with manufacturer."""
    return await service.list_purchase_orders()


@router.post("/")
async def create_purchase_order(sku: str, quantity: int):
    """Create a purchase order with the manufacturer."""
    try:
        return await service.create_purchase_order(sku, quantity)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{po_id}/sync")
async def sync_purchase_order(po_id: int):
    """Sync purchase order status with manufacturer."""
    try:
        # Get local PO
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PurchaseOrderDB).where(PurchaseOrderDB.id == po_id)
            )
            po_row = result.first()
            if not po_row:
                raise HTTPException(status_code=404, detail="Purchase order not found")

            po = po_row[0]

            # Get status from manufacturer
            if po.manufacturer_po_id:
                manufacturer_data = await service.manufacturer_client.get_order(po.manufacturer_po_id)

                # Update local status
                await session.execute(
                    update(PurchaseOrderDB)
                    .where(PurchaseOrderDB.id == po_id)
                    .values(
                        status=manufacturer_data.get("status", po.status),
                        received_day=manufacturer_data.get("received_day"),
                    )
                )
                await session.commit()

                return {"message": f"Purchase order {po_id} synced", "status": manufacturer_data.get("status")}
            else:
                return {"message": "No manufacturer PO ID to sync"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
