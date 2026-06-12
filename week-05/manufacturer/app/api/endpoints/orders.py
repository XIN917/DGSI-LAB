"""Manufacturing Order API endpoints."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.event import EventLog
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/orders", tags=["orders"])


class BOMRequirement(BaseModel):
    required: float
    available: float
    sufficient: bool
    shortage: float


class OrderResponse(BaseModel):
    id: int
    product_model: str
    quantity_needed: float
    quantity_produced: float
    status: str
    created_date: str
    started_date: Optional[str] = None
    completed_date: Optional[str] = None
    failure_reason: Optional[str] = None
    bom_requirements: Optional[dict] = None


class CreateOrderRequest(BaseModel):
    product_model: str
    quantity: float


@router.get("", response_model=List[OrderResponse])
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all manufacturing orders (newest first)."""
    svc = OrderService(db)
    orders = svc.get_all()
    return [_serialize(o) for o in orders]


@router.get("/pending", response_model=List[OrderResponse])
def list_pending_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List pending manufacturing orders with BOM requirements."""
    svc = OrderService(db)
    orders = svc.get_pending()
    return [_serialize(o, include_bom=True, svc=svc) for o in orders]


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get order details including BOM breakdown."""
    svc = OrderService(db)
    order = svc.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order #{order_id} not found")
    return _serialize(order, include_bom=True, svc=svc)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    body: CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new manufacturing order manually."""
    svc = OrderService(db)
    order = svc.create(
        product_model=body.product_model,
        quantity=Decimal(str(body.quantity)),
        created_date=datetime.utcnow(),
    )
    event = EventLog(
        event_type="order_created_manual",
        event_date=datetime.utcnow(),
        details=str({
            "order_id": order.id,
            "model": body.product_model,
            "quantity": body.quantity,
            "user": current_user.username,
        }),
    )
    db.add(event)
    db.commit()
    return _serialize(order, include_bom=True, svc=svc)


@router.post("/{order_id}/release")
def release_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Release an order to production (reserves required materials)."""
    svc = OrderService(db)
    success, error = svc.release(order_id)
    if not success:
        raise HTTPException(status_code=400, detail=error)

    order = svc.get_by_id(order_id)
    event = EventLog(
        event_type="order_released",
        event_date=datetime.utcnow(),
        details=str({
            "order_id": order_id,
            "model": order.product_model,
            "quantity": float(order.quantity_needed),
            "user": current_user.username,
        }),
    )
    db.add(event)
    db.commit()
    return _serialize(order)


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Cancel an order and release any reserved materials."""
    svc = OrderService(db)
    order = svc.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order #{order_id} not found")
    if order.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel a completed order")

    success = svc.cancel(order_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to cancel order")

    event = EventLog(
        event_type="order_cancelled",
        event_date=datetime.utcnow(),
        details=str({"order_id": order_id, "user": current_user.username}),
    )
    db.add(event)
    db.commit()
    return {"message": f"Order #{order_id} cancelled"}


def _serialize(order, include_bom: bool = False, svc: OrderService = None) -> dict:
    result = {
        "id": order.id,
        "product_model": order.product_model,
        "quantity_needed": float(order.quantity_needed),
        "quantity_produced": float(order.quantity_produced),
        "status": order.status,
        "created_date": order.created_date.isoformat() if order.created_date else None,
        "started_date": order.started_date.isoformat() if order.started_date else None,
        "completed_date": order.completed_date.isoformat() if order.completed_date else None,
        "failure_reason": order.failure_reason,
    }
    if include_bom and svc:
        result["bom_requirements"] = svc.calculate_bom_requirements(order)
    return result
