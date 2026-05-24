"""JSON import/export utilities for full game state."""
import json
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.product import ProductModel, BOMItem
from app.models.inventory import Inventory
from app.models.purchase_order import Supplier, SupplierProduct, PurchaseOrder
from app.models.order import ManufacturingOrder
from app.models.event import EventLog
from app.models.simulation import SimulationState
from app.core.security import get_password_hash


def export_full_state(db: Session) -> dict:
    """Export the complete simulation state as a JSON-serialisable dict."""
    sim = db.query(SimulationState).first()

    models = db.query(ProductModel).all()
    suppliers = db.query(Supplier).all()
    inventory = db.query(Inventory).all()
    orders = db.query(ManufacturingOrder).all()
    pos = db.query(PurchaseOrder).all()
    events = db.query(EventLog).order_by(EventLog.id.asc()).all()

    return {
        "exported_at": datetime.utcnow().isoformat(),
        "simulation_state": {
            "current_day": sim.current_day if sim else 1,
            "current_date": sim.current_date if sim else "2026-04-01",
            "capacity_per_day": sim.capacity_per_day if sim else 250,
            "warehouse_capacity": sim.warehouse_capacity if sim else 1000,
            "demand_params": json.loads(sim.demand_params) if sim and sim.demand_params else {},
        },
        "models": [
            {
                "id": m.id,
                "name": m.name,
                "assembly_time_days": m.assembly_time_days,
                "bom": [
                    {
                        "material_name": b.material_name,
                        "quantity_required": float(b.quantity_required),
                        "pcb_ref": b.pcb_ref,
                    }
                    for b in m.bom_items
                ],
            }
            for m in models
        ],
        "suppliers": [
            {
                "id": s.id,
                "name": s.name,
                "lead_time_days": s.lead_time_days,
                "active": s.active,
                "products": [
                    {
                        "id": p.id,
                        "product_name": p.product_name,
                        "base_unit_cost": float(p.base_unit_cost),
                        "packaging_unit": p.packaging_unit,
                        "packaging_qty": p.packaging_qty,
                        "discount_tiers": json.loads(p.discount_tiers) if p.discount_tiers else [],
                    }
                    for p in s.products
                ],
            }
            for s in suppliers
        ],
        "inventory": [
            {
                "product_name": i.product_name,
                "quantity": float(i.quantity),
                "reserved_quantity": float(i.reserved_quantity),
                "unit_type": i.unit_type,
            }
            for i in inventory
        ],
        "manufacturing_orders": [
            {
                "id": o.id,
                "product_model": o.product_model,
                "quantity_needed": float(o.quantity_needed),
                "quantity_produced": float(o.quantity_produced),
                "status": o.status,
                "created_date": o.created_date.isoformat() if o.created_date else None,
                "started_date": o.started_date.isoformat() if o.started_date else None,
                "completed_date": o.completed_date.isoformat() if o.completed_date else None,
                "failure_reason": o.failure_reason,
            }
            for o in orders
        ],
        "purchase_orders": [
            {
                "id": p.id,
                "supplier_id": p.supplier_id,
                "product_name": p.product_name,
                "quantity_ordered": float(p.quantity_ordered),
                "quantity_delivered": float(p.quantity_delivered),
                "unit_cost": float(p.unit_cost),
                "order_date": p.order_date.isoformat() if p.order_date else None,
                "expected_delivery": p.expected_delivery.isoformat() if p.expected_delivery else None,
                "actual_delivery": p.actual_delivery.isoformat() if p.actual_delivery else None,
                "status": p.status,
            }
            for p in pos
        ],
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "event_date": e.event_date.isoformat() if e.event_date else None,
                "details": e.details,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


def import_full_state(db: Session, data: dict) -> dict:
    """
    Import a full game state export.
    CAUTION: This clears all existing simulation data before importing.
    """
    # Validate top-level keys
    required_keys = {"simulation_state", "models", "suppliers", "inventory"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Import data missing required keys: {missing}")

    # Clear existing simulation data (preserve users)
    db.query(EventLog).delete()
    db.query(PurchaseOrder).delete()
    db.query(ManufacturingOrder).delete()
    db.query(Inventory).delete()
    db.query(SupplierProduct).delete()
    db.query(Supplier).delete()
    db.query(BOMItem).delete()
    db.query(ProductModel).delete()
    db.query(SimulationState).delete()
    db.commit()

    # Restore simulation state
    sim_data = data["simulation_state"]
    state = SimulationState(
        current_day=sim_data.get("current_day", 1),
        current_date=sim_data.get("current_date", "2026-04-01"),
        capacity_per_day=sim_data.get("capacity_per_day", 250),
        warehouse_capacity=sim_data.get("warehouse_capacity", 1000),
        demand_params=json.dumps(sim_data.get("demand_params", {})),
    )
    db.add(state)

    # Restore models + BOMs
    for m in data.get("models", []):
        model = ProductModel(id=m["id"], name=m["name"], assembly_time_days=m.get("assembly_time_days", 1))
        db.add(model)
        for b in m.get("bom", []):
            db.add(BOMItem(
                model_id=m["id"],
                material_name=b["material_name"],
                quantity_required=Decimal(str(b["quantity_required"])),
                pcb_ref=b.get("pcb_ref"),
            ))

    # Restore suppliers
    for s in data.get("suppliers", []):
        supplier = Supplier(id=s["id"], name=s["name"], lead_time_days=s["lead_time_days"], active=s.get("active", True))
        db.add(supplier)
        for p in s.get("products", []):
            db.add(SupplierProduct(
                supplier_id=s["id"],
                product_name=p["product_name"],
                base_unit_cost=Decimal(str(p["base_unit_cost"])),
                packaging_unit=p.get("packaging_unit"),
                packaging_qty=p.get("packaging_qty"),
                discount_tiers=json.dumps(p.get("discount_tiers", [])),
            ))

    # Restore inventory
    for i in data.get("inventory", []):
        db.add(Inventory(
            product_name=i["product_name"],
            quantity=Decimal(str(i["quantity"])),
            reserved_quantity=Decimal(str(i.get("reserved_quantity", 0))),
            unit_type=i.get("unit_type", "raw"),
        ))

    # Restore manufacturing orders
    for o in data.get("manufacturing_orders", []):
        db.add(ManufacturingOrder(
            id=o.get("id"),
            product_model=o["product_model"],
            quantity_needed=Decimal(str(o["quantity_needed"])),
            quantity_produced=Decimal(str(o.get("quantity_produced", 0))),
            status=o.get("status", "pending"),
            created_date=datetime.fromisoformat(o["created_date"]) if o.get("created_date") else datetime.utcnow(),
            started_date=datetime.fromisoformat(o["started_date"]) if o.get("started_date") else None,
            completed_date=datetime.fromisoformat(o["completed_date"]) if o.get("completed_date") else None,
            failure_reason=o.get("failure_reason"),
        ))

    # Restore purchase orders
    for p in data.get("purchase_orders", []):
        db.add(PurchaseOrder(
            id=p.get("id"),
            supplier_id=p["supplier_id"],
            product_name=p["product_name"],
            quantity_ordered=Decimal(str(p["quantity_ordered"])),
            quantity_delivered=Decimal(str(p.get("quantity_delivered", 0))),
            unit_cost=Decimal(str(p["unit_cost"])),
            order_date=datetime.fromisoformat(p["order_date"]) if p.get("order_date") else datetime.utcnow(),
            expected_delivery=datetime.fromisoformat(p["expected_delivery"]) if p.get("expected_delivery") else datetime.utcnow(),
            actual_delivery=datetime.fromisoformat(p["actual_delivery"]) if p.get("actual_delivery") else None,
            status=p.get("status", "pending"),
        ))

    # Restore events (optional)
    for e in data.get("events", []):
        db.add(EventLog(
            id=e.get("id"),
            event_type=e["event_type"],
            event_date=datetime.fromisoformat(e["event_date"]) if e.get("event_date") else datetime.utcnow(),
            details=e.get("details", ""),
        ))

    db.commit()
    return {"status": "imported", "models": len(data.get("models", [])), "events": len(data.get("events", []))}
