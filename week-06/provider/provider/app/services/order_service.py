"""Order service for Provider app."""
from typing import List, Dict, Any, Optional
from datetime import datetime

from provider.app.db import get_session
from provider.app.models.order import Order
from provider.app.models.event import Event
from provider.app.models.stock import Stock
from provider.app.services.catalog_service import get_product_by_id, calculate_price


def create_order(buyer: str, product_id: int, quantity: int) -> Dict[str, Any]:
    """Create a new order."""
    session = get_session()
    try:
        # Get product info
        product = get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found")
        
        # Calculate price
        unit_price = calculate_price(product_id, quantity)
        total_price = unit_price * quantity
        
        # Get current day and calculate expected delivery
        current_day = get_current_day()
        expected_delivery = current_day + product["lead_time_days"]
        
        # Check stock
        stock = session.query(Stock).filter_by(product_id=product_id).first()
        has_stock = stock and stock.quantity >= quantity
        
        # Create order
        order = Order(
            buyer=buyer,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            placed_day=current_day,
            expected_delivery_day=expected_delivery,
            status="pending" if not has_stock else "confirmed",
        )
        session.add(order)
        session.flush()
        
        # Log event
        event = Event(
            sim_day=current_day,
            event_type="order_placed",
            entity_type="order",
            entity_id=order.id,
            detail=f"Order {order.id}: {buyer} ordered {quantity}x {product['name']} at €{unit_price}/each (total: €{total_price})",
        )
        session.add(event)
        
        # If stock available, reserve it
        if has_stock:
            stock.quantity -= quantity
            log_event(session, current_day, "order_confirmed", "order", order.id, 
                     f"Order {order.id} confirmed - stock reserved")
        
        session.commit()
        return order.to_dict()
    finally:
        session.close()


def get_order(order_id: int) -> Optional[Dict[str, Any]]:
    """Get an order by ID."""
    session = get_session()
    try:
        order = session.query(Order).filter_by(id=order_id).first()
        if not order:
            return None
        
        return order.to_dict()
    finally:
        session.close()


def get_orders(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all orders, optionally filtered by status."""
    session = get_session()
    try:
        query = session.query(Order)
        
        if status:
            query = query.filter_by(status=status)
        
        orders = query.order_by(Order.id.desc()).all()
        return [o.to_dict() for o in orders]
    finally:
        session.close()


def advance_day() -> Dict[str, Any]:
    """Advance the simulation by one day and process orders."""
    session = get_session()
    try:
        from provider.app.models.sim_state import SimState
        
        # Get current day
        state = session.query(SimState).filter_by(key="current_day").first()
        current_day = int(state.value) if state else 0
        
        # Process deliveries before shipments so a newly shipped order cannot be
        # delivered in the same day-advance cycle.
        orders_to_deliver = session.query(Order).filter(
            Order.status == "shipped",
            Order.expected_delivery_day <= current_day
        ).all()
        
        for order in orders_to_deliver:
            order.status = "delivered"
            order.delivered_day = current_day
            log_event(session, current_day, "order_delivered", "order", order.id,
                     f"Order {order.id} delivered to {order.buyer}")

        # Ship confirmed orders one day before their expected delivery day.
        orders_to_ship = session.query(Order).filter(
            Order.status == "confirmed",
            Order.expected_delivery_day <= current_day + 1
        ).all()
        
        for order in orders_to_ship:
            order.status = "shipped"
            order.shipped_day = current_day
            log_event(session, current_day, "order_shipped", "order", order.id,
                     f"Order {order.id} shipped")
        
        # Increment day
        new_day = current_day + 1
        if state:
            state.value = str(new_day)
        else:
            state = SimState(key="current_day", value=str(new_day))
            session.add(state)
        
        log_event(session, new_day, "day_advanced", None, None, f"Day advanced to {new_day}")
        
        session.commit()
        
        return {
            "previous_day": current_day,
            "current_day": new_day,
            "orders_shipped": len(orders_to_ship),
            "orders_delivered": len(orders_to_deliver),
        }
    finally:
        session.close()


def get_current_day() -> int:
    """Get the current simulation day."""
    session = get_session()
    try:
        from provider.app.models.sim_state import SimState
        state = session.query(SimState).filter_by(key="current_day").first()
        return int(state.value) if state else 0
    finally:
        session.close()


def log_event(session, sim_day: int, event_type: str, entity_type: str, entity_id: int, detail: str):
    """Log an event."""
    event = Event(
        sim_day=sim_day,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    session.add(event)
