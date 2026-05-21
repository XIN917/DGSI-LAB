from fastapi import APIRouter, HTTPException
from typing import List

from app.models.order import CustomerOrder
from app.services.retailer_service import RetailerService

router = APIRouter()
service = RetailerService()


@router.get("/", response_model=List[CustomerOrder])
async def list_customer_orders():
    """List all customer orders."""
    return await service.list_customer_orders()


@router.post("/", response_model=CustomerOrder)
async def create_customer_order(
    sku: str,
    quantity: int,
    customer_name: str = None,
    notes: str = None,
):
    """Create a new customer order."""
    try:
        return await service.create_customer_order(sku, quantity, customer_name, notes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}", response_model=CustomerOrder)
async def get_customer_order(order_id: int):
    """Get a specific customer order by ID."""
    orders = await service.list_customer_orders()
    for order in orders:
        if order.id == order_id:
            return order
    raise HTTPException(status_code=404, detail="Order not found")
