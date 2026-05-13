"""Export/Import service for Provider app."""
import json
from typing import Dict, Any
from provider.app.db import get_session
from provider.app.models.product import Product
from provider.app.models.pricing_tier import PricingTier
from provider.app.models.stock import Stock
from provider.app.models.order import Order
from provider.app.models.event import Event
from provider.app.models.sim_state import SimState


def export_state() -> str:
    """Export all state to JSON."""
    session = get_session()
    try:
        data = {
            "products": [],
            "orders": [],
            "events": [],
            "sim_state": {},
        }
        
        # Export products with pricing
        products = session.query(Product).all()
        for product in products:
            tiers = session.query(PricingTier).filter_by(product_id=product.id).all()
            stock = session.query(Stock).filter_by(product_id=product.id).first()
            
            data["products"].append({
                "product": product.to_dict(),
                "pricing": [t.to_dict() for t in tiers],
                "stock": stock.to_dict() if stock else {"product_id": product.id, "quantity": 0},
            })
        
        # Export orders
        orders = session.query(Order).all()
        data["orders"] = [o.to_dict() for o in orders]
        
        # Export events
        events = session.query(Event).all()
        data["events"] = [e.to_dict() for e in events]
        
        # Export sim state
        states = session.query(SimState).all()
        data["sim_state"] = {s.key: s.value for s in states}
        
        # Write to file
        output_file = "provider-export.json"
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        
        return output_file
    finally:
        session.close()


def import_state(file: str) -> bool:
    """Import state from JSON."""
    session = get_session()
    try:
        with open(file, "r") as f:
            data = json.load(f)
        
        # Import sim state
        for key, value in data.get("sim_state", {}).items():
            state = session.query(SimState).filter_by(key=key).first()
            if state:
                state.value = value
            else:
                state = SimState(key=key, value=value)
                session.add(state)
        
        # Import products and pricing
        for product_data in data.get("products", []):
            product_info = product_data["product"]
            product = session.query(Product).filter_by(id=product_info["id"]).first()
            if product:
                product.name = product_info["name"]
                product.description = product_info["description"]
                product.lead_time_days = product_info["lead_time_days"]
            
            # Update pricing tiers
            for tier_data in product_data.get("pricing", []):
                tier = session.query(PricingTier).filter_by(id=tier_data["id"]).first()
                if tier:
                    tier.min_quantity = tier_data["min_quantity"]
                    tier.unit_price = tier_data["unit_price"]
            
            # Update stock
            stock_data = product_data.get("stock", {})
            if stock_data:
                stock = session.query(Stock).filter_by(product_id=stock_data["product_id"]).first()
                if stock:
                    stock.quantity = stock_data["quantity"]
        
        # Import orders
        for order_data in data.get("orders", []):
            order = session.query(Order).filter_by(id=order_data["id"]).first()
            if order:
                order.status = order_data["status"]
                order.shipped_day = order_data.get("shipped_day")
                order.delivered_day = order_data.get("delivered_day")
        
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error importing state: {e}")
        return False
    finally:
        session.close()