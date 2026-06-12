"""JSON import/export utilities for Provider state."""
import json
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.product import Product, PricingTier, Stock
from app.models.order import Order
from app.models.event import Event
from app.models.simulation import SimState

def export_full_state(db: Session) -> dict:
    """Export the complete provider state as a JSON-serialisable dict."""
    sim_states = db.query(SimState).all()
    products = db.query(Product).all()
    orders = db.query(Order).all()
    events = db.query(Event).order_by(Event.id.asc()).all()

    return {
        "exported_at": datetime.utcnow().isoformat(),
        "sim_state": {s.key: s.value for s in sim_states},
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "lead_time_days": p.lead_time_days,
                "pricing_tiers": [
                    {
                        "min_quantity": t.min_quantity,
                        "unit_price": float(t.unit_price)
                    }
                    for t in p.pricing_tiers
                ],
                "stock": p.stock.quantity if p.stock else 0
            }
            for p in products
        ],
        "orders": [
            {
                "id": o.id,
                "buyer": o.buyer,
                "product_id": o.product_id,
                "quantity": o.quantity,
                "unit_price": float(o.unit_price),
                "total_price": float(o.total_price),
                "placed_day": o.placed_day,
                "expected_delivery_day": o.expected_delivery_day,
                "shipped_day": o.shipped_day,
                "delivered_day": o.delivered_day,
                "status": o.status
            }
            for o in orders
        ],
        "events": [
            {
                "id": e.id,
                "sim_day": e.sim_day,
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "detail": e.detail,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in events
        ]
    }

def import_full_state(db: Session, data: dict) -> dict:
    """
    Import a full provider state export.
    CAUTION: This clears all existing provider data before importing.
    """
    # Validate top-level keys
    required_keys = {"sim_state", "products"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Import data missing required keys: {missing}")

    # Clear existing data
    db.query(Event).delete()
    db.query(Order).delete()
    db.query(Stock).delete()
    db.query(PricingTier).delete()
    db.query(Product).delete()
    db.query(SimState).delete()
    db.commit()

    # Restore simulation state
    for key, value in data["sim_state"].items():
        db.add(SimState(key=key, value=str(value)))

    # Restore products + pricing + stock
    for p_data in data.get("products", []):
        product = Product(
            id=p_data.get("id"),
            name=p_data["name"],
            description=p_data.get("description"),
            lead_time_days=p_data["lead_time_days"]
        )
        db.add(product)
        db.flush() # To get product ID if not provided

        for t_data in p_data.get("pricing_tiers", []):
            db.add(PricingTier(
                product_id=product.id,
                min_quantity=t_data["min_quantity"],
                unit_price=Decimal(str(t_data["unit_price"]))
            ))
        
        db.add(Stock(
            product_id=product.id,
            quantity=p_data.get("stock", 0)
        ))

    # Restore orders
    for o_data in data.get("orders", []):
        db.add(Order(
            id=o_data.get("id"),
            buyer=o_data["buyer"],
            product_id=o_data["product_id"],
            quantity=o_data["quantity"],
            unit_price=Decimal(str(o_data["unit_price"])),
            total_price=Decimal(str(o_data["total_price"])),
            placed_day=o_data["placed_day"],
            expected_delivery_day=o_data["expected_delivery_day"],
            shipped_day=o_data.get("shipped_day"),
            delivered_day=o_data.get("delivered_day"),
            status=o_data["status"]
        ))

    # Restore events
    for e_data in data.get("events", []):
        db.add(Event(
            id=e_data.get("id"),
            sim_day=e_data["sim_day"],
            event_type=e_data["event_type"],
            entity_type=e_data.get("entity_type"),
            entity_id=e_data.get("entity_id"),
            detail=e_data.get("detail"),
            created_at=datetime.fromisoformat(e_data["created_at"]) if e_data.get("created_at") else None
        ))

    db.commit()
    return {
        "status": "imported",
        "products": len(data.get("products", [])),
        "orders": len(data.get("orders", [])),
        "events": len(data.get("events", []))
    }
