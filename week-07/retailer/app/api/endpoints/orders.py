from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from app.models.order import CustomerOrder
from app.services.retailer_service import RetailerService
from app.core.database import get_db
from app.api.schemas import OrderCreate

router = APIRouter()


@router.get("", response_model=List[CustomerOrder])
def list_customer_orders(db: Session = Depends(get_db)):
    """List all customer orders."""
    service = RetailerService(db)
    return service.list_customer_orders()


@router.post("", response_model=CustomerOrder)
def create_customer_order(order: OrderCreate, db: Session = Depends(get_db)):
    """Create a new customer order."""
    service = RetailerService(db)
    try:
        return service.create_customer_order(
            sku=order.model,
            quantity=order.quantity,
            customer_name=order.customer,
            notes=order.notes
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}", response_model=CustomerOrder)
def get_customer_order(order_id: int, db: Session = Depends(get_db)):
    """Get a specific customer order by ID."""
    service = RetailerService(db)
    orders = service.list_customer_orders()
    for order in orders:
        if order.id == order_id:
            return order
    raise HTTPException(status_code=404, detail="Order not found")
