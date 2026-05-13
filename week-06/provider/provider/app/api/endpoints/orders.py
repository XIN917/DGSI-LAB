"""Order endpoints for Provider app."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from provider.app.services.order_service import (
    create_order,
    get_order,
    get_orders,
)

router = APIRouter(prefix="/api", tags=["orders"])


class OrderRequest(BaseModel):
    buyer: str
    product_id: int
    quantity: int


@router.post("/orders")
def place_order(request: OrderRequest):
    """Place a new purchase order."""
    try:
        order = create_order(
            buyer=request.buyer,
            product_id=request.product_id,
            quantity=request.quantity,
        )
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders")
def list_orders(status: Optional[str] = None):
    """List all orders, optionally filtered by status."""
    return get_orders(status=status)


@router.get("/orders/{order_id}")
def get_order_details(order_id: int):
    """Get order details."""
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order