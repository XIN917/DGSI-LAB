"""Purchase Order API endpoints."""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.event import EventLog
from app.models.purchase_order import PurchaseOrder, Supplier, SupplierProduct

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
def list_purchase_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all purchase orders."""
    pos = db.query(PurchaseOrder).order_by(PurchaseOrder.order_date.desc()).all()
    return [_serialize(po, db) for po in pos]


@router.get("/{po_id}", response_model=POResponse)
def get_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get purchase order details."""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail=f"Purchase order #{po_id} not found")
    return _serialize(po, db)


@router.post("", response_model=POResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    body: CreatePORequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a purchase order. Applies bulk discount tiers automatically."""
    supplier = db.query(Supplier).filter(Supplier.id == body.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier #{body.supplier_id} not found")

    sup_product = db.query(SupplierProduct).filter(
        SupplierProduct.supplier_id == body.supplier_id,
        SupplierProduct.product_name == body.product_name,
    ).first()
    if not sup_product:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier #{body.supplier_id} does not carry '{body.product_name}'",
        )

    unit_cost = _calculate_unit_cost(sup_product, body.quantity)

    from app.services.simulation_engine import SimulationEngine
    engine = SimulationEngine(db)
    sim_now = engine.current_date
    expected = sim_now + timedelta(days=supplier.lead_time_days)

    po = PurchaseOrder(
        supplier_id=body.supplier_id,
        product_name=body.product_name,
        quantity_ordered=Decimal(str(body.quantity)),
        quantity_delivered=Decimal("0"),
        unit_cost=Decimal(str(unit_cost)),
        order_date=datetime.combine(sim_now, datetime.min.time()),
        expected_delivery=datetime.combine(expected, datetime.min.time()),
        status="pending",
    )
    db.add(po)

    event = EventLog(
        event_type="po_created",
        event_date=datetime.combine(sim_now, datetime.min.time()),
        details=str({
            "supplier": supplier.name,
            "product": body.product_name,
            "quantity": body.quantity,
            "unit_cost": unit_cost,
            "total_cost": unit_cost * body.quantity,
            "expected_delivery": expected.isoformat(),
            "user": current_user.username,
        }),
    )
    db.add(event)
    db.commit()
    db.refresh(po)
    return _serialize(po, db)


@router.post("/{po_id}/cancel")
def cancel_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Cancel a pending purchase order."""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail=f"Purchase order #{po_id} not found")
    if po.status in ("delivered", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel PO with status '{po.status}'")

    po.status = "cancelled"
    event = EventLog(
        event_type="po_cancelled",
        event_date=datetime.utcnow(),
        details=str({"po_id": po_id, "user": current_user.username}),
    )
    db.add(event)
    db.commit()
    return {"message": f"Purchase order #{po_id} cancelled"}


def _calculate_unit_cost(sup_product: SupplierProduct, quantity: float) -> float:
    """Apply bulk discount tiers and return effective unit cost."""
    base = float(sup_product.base_unit_cost)
    if not sup_product.discount_tiers:
        return base

    tiers = json.loads(sup_product.discount_tiers) if isinstance(sup_product.discount_tiers, str) else sup_product.discount_tiers
    discount_pct = 0.0
    for tier in sorted(tiers, key=lambda t: t["min_qty"]):
        if quantity >= tier["min_qty"]:
            discount_pct = tier["discount_pct"]
    return round(base * (1 - discount_pct / 100), 4)


def _serialize(po: PurchaseOrder, db: Session) -> dict:
    supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
    qty = float(po.quantity_ordered)
    unit = float(po.unit_cost)
    return {
        "id": po.id,
        "supplier_id": po.supplier_id,
        "supplier_name": supplier.name if supplier else None,
        "product_name": po.product_name,
        "quantity_ordered": qty,
        "quantity_delivered": float(po.quantity_delivered),
        "unit_cost": unit,
        "total_cost": round(qty * unit, 2),
        "order_date": po.order_date.isoformat() if po.order_date else None,
        "expected_delivery": po.expected_delivery.isoformat() if po.expected_delivery else None,
        "actual_delivery": po.actual_delivery.isoformat() if po.actual_delivery else None,
        "status": po.status,
    }
