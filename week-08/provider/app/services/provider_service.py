from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.product import Product, PricingTier, Stock
from app.models.order import Order
from app.models.event import Event
from app.models.simulation import SimState

class ProviderService:
    def __init__(self, db: Session):
        self.db = db

    # --- Simulation State ---
    def get_current_day(self) -> int:
        state = self.db.query(SimState).filter(SimState.key == "current_day").first()
        if not state:
            state = SimState(key="current_day", value="0")
            self.db.add(state)
            self.db.commit()
            return 0
        return int(state.value)

    def advance_day(self) -> int:
        current_day = self.get_current_day()
        new_day = current_day + 1
        
        state = self.db.query(SimState).filter(SimState.key == "current_day").first()
        state.value = str(new_day)
        
        self.log_event(new_day, "DAY_ADVANCE", detail=f"Advanced to day {new_day}")
        
        # Process order state machine
        self._process_orders_state_machine(new_day)
        
        self.db.commit()
        return new_day

    def _process_orders_state_machine(self, current_day: int):
        # Shipped -> Delivered (When expected_delivery_day is reached)
        shipped_orders = self.db.query(Order).filter(Order.status == "SHIPPED").all()
        for order in shipped_orders:
            if current_day >= order.expected_delivery_day:
                order.status = "DELIVERED"
                order.delivered_day = current_day
                self.log_event(current_day, "ORDER_DELIVERED", "Order", order.id)

        # InProgress -> Shipped
        inprogress_orders = self.db.query(Order).filter(Order.status == "InProgress").all()
        for order in inprogress_orders:
            order.status = "SHIPPED"
            order.shipped_day = current_day
            self.log_event(current_day, "ORDER_SHIPPED", "Order", order.id)

        # Confirmed -> InProgress
        confirmed_orders = self.db.query(Order).filter(Order.status == "CONFIRMED").all()
        for order in confirmed_orders:
            order.status = "InProgress"
            self.log_event(current_day, "ORDER_IN_PROGRESS", "Order", order.id)

        # Pending -> Confirmed (Auto-confirm if stock available)
        pending_orders = self.db.query(Order).filter(Order.status == "PENDING").all()
        for order in pending_orders:
            stock = self.db.query(Stock).filter(Stock.product_id == order.product_id).first()
            if stock and stock.quantity >= order.quantity:
                stock.quantity -= order.quantity
                order.status = "CONFIRMED"
                self.log_event(current_day, "ORDER_CONFIRMED", "Order", order.id, f"Order {order.id} confirmed")

    # --- Catalog & Stock ---
    def get_catalog(self) -> List[Product]:
        return self.db.query(Product).all()

    def get_stock(self) -> List[Stock]:
        return self.db.query(Stock).all()

    def restock(self, product_id: int, quantity: int):
        stock = self.db.query(Stock).filter(Stock.product_id == product_id).first()
        if not stock:
            stock = Stock(product_id=product_id, quantity=quantity)
            self.db.add(stock)
        else:
            stock.quantity += quantity
        
        current_day = self.get_current_day()
        self.log_event(current_day, "RESTOCK", "Product", product_id, f"Added {quantity} units")
        self.db.commit()

    # --- Orders ---
    def place_order(self, buyer: str, product_id: int, quantity: int) -> Order:
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        # Determine unit price based on tiers
        unit_price = self._calculate_unit_price(product_id, quantity)
        total_price = unit_price * quantity
        
        current_day = self.get_current_day()
        expected_delivery_day = current_day + product.lead_time_days
        
        order = Order(
            buyer=buyer,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            placed_day=current_day,
            expected_delivery_day=expected_delivery_day,
            status="PENDING"
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        
        self.log_event(current_day, "ORDER_PLACED", "Order", order.id, f"Buyer: {buyer}, Qty: {quantity}")
        return order

    def _calculate_unit_price(self, product_id: int, quantity: int) -> Decimal:
        tiers = self.db.query(PricingTier).filter(PricingTier.product_id == product_id).order_by(PricingTier.min_quantity.desc()).all()
        for tier in tiers:
            if quantity >= tier.min_quantity:
                return tier.unit_price
        # Fallback to first tier or some default?
        if tiers:
            return tiers[-1].unit_price
        return Decimal("0.00")

    def get_orders(self, status: Optional[str] = None) -> List[Order]:
        query = self.db.query(Order)
        if status:
            query = query.filter(Order.status == status)
        return query.all()

    def get_order(self, order_id: int) -> Optional[Order]:
        return self.db.query(Order).filter(Order.id == order_id).first()

    def set_price(self, product_id: int, min_quantity: int, unit_price: Decimal):
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")
        
        tier = self.db.query(PricingTier).filter(
            PricingTier.product_id == product_id,
            PricingTier.min_quantity == min_quantity
        ).first()
        
        if tier:
            tier.unit_price = unit_price
        else:
            tier = PricingTier(product_id=product_id, min_quantity=min_quantity, unit_price=unit_price)
            self.db.add(tier)
        
        current_day = self.get_current_day()
        self.log_event(current_day, "PRICE_UPDATE", "Product", product_id, f"Set tier {min_quantity} to {unit_price}€")
        self.db.commit()

    # --- Events ---
    def log_event(self, sim_day: int, event_type: str, entity_type: str = None, entity_id: int = None, detail: str = None):
        event = Event(
            sim_day=sim_day,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail
        )
        self.db.add(event)
        # We don't commit here to allow batching if needed
