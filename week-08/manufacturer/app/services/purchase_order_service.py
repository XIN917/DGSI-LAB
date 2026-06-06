"""Purchase order service."""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.event import EventLog
from app.models.purchase_order import PurchaseOrder, Supplier, SupplierProduct


class PurchaseOrderService:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[dict]:
        pos = self.db.query(PurchaseOrder).order_by(PurchaseOrder.order_date.desc()).all()
        return [self._serialize(po) for po in pos]

    def get(self, po_id: int) -> Optional[dict]:
        po = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        return self._serialize(po) if po else None

    def create(self, supplier_id: int, product_name: str, quantity: float) -> dict:
        supplier = self.db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier #{supplier_id} not found")

        if supplier.is_external:
            from app.services.external_supplier_service import ExternalSupplierService
            service = ExternalSupplierService(self.db)
            po = service.place_order(supplier.name, product_name, int(quantity))
            return self._serialize(po)

        sup_product = self.db.query(SupplierProduct).filter(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.product_name == product_name,
        ).first()
        if not sup_product:
            raise ValueError(f"Supplier #{supplier_id} does not carry '{product_name}'")

        unit_cost = self._calculate_unit_cost(sup_product, quantity)

        from app.services.simulation_engine import SimulationEngine
        engine = SimulationEngine(self.db)
        sim_now = engine.current_date
        expected = sim_now + timedelta(days=supplier.lead_time_days)

        po = PurchaseOrder(
            supplier_id=supplier_id,
            product_name=product_name,
            quantity_ordered=Decimal(str(quantity)),
            quantity_delivered=Decimal("0"),
            unit_cost=Decimal(str(unit_cost)),
            order_date=datetime.combine(sim_now, datetime.min.time()),
            expected_delivery=datetime.combine(expected, datetime.min.time()),
            status="pending",
        )
        self.db.add(po)

        event = EventLog(
            event_type="po_created",
            event_date=datetime.combine(sim_now, datetime.min.time()),
            details=str({
                "supplier": supplier.name,
                "product": product_name,
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total_cost": round(unit_cost * quantity, 4),
                "expected_delivery": expected.isoformat(),
            }),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(po)
        return self._serialize(po)

    def cancel(self, po_id: int) -> dict:
        po = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            raise ValueError(f"Purchase order #{po_id} not found")
        if po.status in ("delivered", "cancelled"):
            raise ValueError(f"Cannot cancel PO with status '{po.status}'")

        po.status = "cancelled"
        event = EventLog(
            event_type="po_cancelled",
            event_date=datetime.utcnow(),
            details=str({"po_id": po_id}),
        )
        self.db.add(event)
        self.db.commit()
        return {"message": f"Purchase order #{po_id} cancelled"}

    def _calculate_unit_cost(self, sup_product: SupplierProduct, quantity: float) -> float:
        base = float(sup_product.base_unit_cost)
        if not sup_product.discount_tiers:
            return base
        tiers = (
            json.loads(sup_product.discount_tiers)
            if isinstance(sup_product.discount_tiers, str)
            else sup_product.discount_tiers
        )
        discount_pct = 0.0
        for tier in sorted(tiers, key=lambda t: t["min_qty"]):
            if quantity >= tier["min_qty"]:
                discount_pct = tier["discount_pct"]
        return round(base * (1 - discount_pct / 100), 4)

    def _serialize(self, po: PurchaseOrder) -> dict:
        supplier = self.db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
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
