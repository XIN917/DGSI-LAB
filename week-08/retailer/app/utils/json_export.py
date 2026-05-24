"""JSON import/export utilities for Retailer."""
import json
from datetime import datetime, UTC
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from pathlib import Path

from app.models.database import (
    CustomerOrderDB,
    InventoryItemDB,
    PurchaseOrderDB,
    EventLogDB,
    SimStateDB,
)

def export_full_state(session: Session) -> dict:
    """Export the complete retailer state as a JSON-serialisable dict."""
    
    # Fetch all data
    customer_orders = session.execute(select(CustomerOrderDB)).scalars().all()
    inventory = session.execute(select(InventoryItemDB)).scalars().all()
    purchase_orders = session.execute(select(PurchaseOrderDB)).scalars().all()
    events = session.execute(select(EventLogDB).order_by(EventLogDB.id)).scalars().all()
    sim_state = session.execute(select(SimStateDB)).scalars().all()

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "sim_state": {s.key: s.value for s in sim_state},
        "inventory": [
            {
                "sku": i.sku,
                "quantity_on_hand": i.quantity_on_hand,
                "quantity_reserved": i.quantity_reserved,
                "retail_price": i.retail_price,
                "last_cost": i.last_cost,
            }
            for i in inventory
        ],
        "customer_orders": [
            {
                "id": o.id,
                "sku": o.sku,
                "quantity": o.quantity,
                "retail_price": o.retail_price,
                "status": o.status,
                "created_day": o.created_day,
                "fulfilled_day": o.fulfilled_day,
                "customer_name": o.customer_name,
                "notes": o.notes,
            }
            for o in customer_orders
        ],
        "purchase_orders": [
            {
                "id": p.id,
                "manufacturer_po_id": p.manufacturer_po_id,
                "sku": p.sku,
                "quantity": p.quantity,
                "wholesale_unit_price": p.wholesale_unit_price,
                "status": p.status,
                "placed_day": p.placed_day,
                "expected_delivery_day": p.expected_delivery_day,
                "received_day": p.received_day,
            }
            for p in purchase_orders
        ],
        "events": [
            {
                "id": e.id,
                "sim_day": e.sim_day,
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "details": e.details,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }

def import_full_state(session: Session, data: dict) -> dict:
    """Import a full retailer state export."""
    
    # Clear existing data
    session.execute(delete(EventLogDB))
    session.execute(delete(PurchaseOrderDB))
    session.execute(delete(CustomerOrderDB))
    session.execute(delete(InventoryItemDB))
    session.execute(delete(SimStateDB))
    
    # Restore Sim State
    for key, value in data.get("sim_state", {}).items():
        session.add(SimStateDB(key=key, value=str(value)))
    
    # Restore Inventory
    for i in data.get("inventory", []):
        session.add(InventoryItemDB(
            sku=i["sku"],
            quantity_on_hand=i["quantity_on_hand"],
            quantity_reserved=i.get("quantity_reserved", 0),
            retail_price=i["retail_price"],
            last_cost=i.get("last_cost"),
        ))
    
    # Restore Customer Orders
    for o in data.get("customer_orders", []):
        session.add(CustomerOrderDB(
            id=o.get("id"),
            sku=o["sku"],
            quantity=o["quantity"],
            retail_price=o["retail_price"],
            status=o.get("status", "pending"),
            created_day=o["created_day"],
            fulfilled_day=o.get("fulfilled_day"),
            customer_name=o.get("customer_name"),
            notes=o.get("notes"),
        ))
    
    # Restore Purchase Orders
    for p in data.get("purchase_orders", []):
        session.add(PurchaseOrderDB(
            id=p.get("id"),
            manufacturer_po_id=p.get("manufacturer_po_id"),
            sku=p["sku"],
            quantity=p["quantity"],
            wholesale_unit_price=p["wholesale_unit_price"],
            retail_unit_price=0.0, # Not in export but required by schema
            status=p.get("status", "pending"),
            placed_day=p["placed_day"],
            expected_delivery_day=p.get("expected_delivery_day"),
            received_day=p.get("received_day"),
        ))
    
    # Restore Events
    for e in data.get("events", []):
        session.add(EventLogDB(
            id=e.get("id"),
            sim_day=e["sim_day"],
            event_type=e["event_type"],
            entity_type=e["entity_type"],
            entity_id=e.get("entity_id"),
            details=e["details"],
            created_at=datetime.fromisoformat(e["created_at"]) if e.get("created_at") else datetime.now(UTC),
        ))
    
    session.commit()
    return {"status": "imported"}
