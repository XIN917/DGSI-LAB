from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.services.provider_service import ProviderService
from app.api.schemas import OrderSchema, OrderCreateSchema

router = APIRouter()

@router.post("/", response_model=OrderSchema)
def place_order(order_in: OrderCreateSchema, db: Session = Depends(get_db)):
    service = ProviderService(db)
    try:
        return service.place_order(order_in.buyer, order_in.product_id, order_in.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[OrderSchema])
def get_orders(status: Optional[str] = None, db: Session = Depends(get_db)):
    service = ProviderService(db)
    return service.get_orders(status=status)

@router.get("/{order_id}", response_model=OrderSchema)
def get_order(order_id: int, db: Session = Depends(get_db)):
    service = ProviderService(db)
    order = service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
