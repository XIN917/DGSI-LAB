"""Simulation engine for day advancement."""
from datetime import datetime, timedelta
from typing import List, Dict
import random
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.event import EventLog
from app.models.order import ManufacturingOrder
from app.models.product import ProductModel, BOMItem
from app.models.purchase_order import PurchaseOrder
from app.core.config import get_settings
from app.services.inventory_service import InventoryService


class SimulationEngine:
    """Engine for running simulation day cycles."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self._load_state()

    def _load_state(self):
        """Load simulation state from database."""
        import json as _json
        from app.models.simulation import SimulationState
        state = self.db.query(SimulationState).first()
        if state:
            self.current_day = state.current_day
            self.current_date = datetime.strptime(state.current_date, "%Y-%m-%d").date()
            self._demand_params = _json.loads(state.demand_params) if state.demand_params else None
            self._capacity_per_day = state.capacity_per_day
        else:
            self.current_day = 1
            self.current_date = datetime.strptime(
                self.settings.SIMULATION_START_DATE, "%Y-%m-%d"
            ).date()
            self._demand_params = None
            self._capacity_per_day = self.settings.DEFAULT_CAPACITY_PER_DAY

    def _save_state(self):
        """Persist simulation state to database."""
        import json as _json
        from app.models.simulation import SimulationState
        state = self.db.query(SimulationState).first()
        if state:
            state.current_day = self.current_day
            state.current_date = self.current_date.isoformat()
        else:
            state = SimulationState(
                current_day=self.current_day,
                current_date=self.current_date.isoformat()
            )
            self.db.add(state)
        self.db.commit()

    def advance_day(self) -> Dict:
        """Advance simulation by one day."""
        events = []

        # Step 1: Process arriving POs first
        po_events = self._process_purchase_orders()
        events.extend(po_events)

        # Step 2: Generate new demand
        demand_events = self._generate_demand()
        events.extend(demand_events)

        # Step 3: Process manufacturing orders within capacity
        order_events = self._process_manufacturing_orders()
        events.extend(order_events)

        # Step 4: Take inventory snapshot
        snapshot_event = self._take_inventory_snapshot()
        events.append(snapshot_event)

        # Increment day counter and persist
        previous_day = self.current_day
        self.current_day += 1
        self.current_date += timedelta(days=1)
        self._save_state()

        return {
            "previous_day": previous_day,
            "new_day": self.current_day,
            "current_date": self.current_date.isoformat(),
            "events_generated": events
        }

    def _process_purchase_orders(self) -> List[Dict]:
        """Process purchase orders due today."""
        events = []

        # Get all pending or partial POs
        all_pos = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.status.in_(["pending", "partial"])
        ).all()

        # Filter in Python to handle date vs datetime comparison correctly
        todays_po = [
            po for po in all_pos 
            if po.expected_delivery.date() <= self.current_date
        ]

        for po in todays_po:
            # Check if partial delivery (~5-10% chance)
            should_be_partial = random.random() < 0.07  # 7% chance

            if should_be_partial and float(po.quantity_ordered - po.quantity_delivered) > 0:
                # Deliver ~70-90% of remaining
                remaining = float(po.quantity_ordered - po.quantity_delivered)
                actual_delivery = int(remaining * random.uniform(0.70, 0.90))

                inv_svc = InventoryService(self.db)
                inv_svc.adjust(po.product_name, Decimal(str(
                    float(inv_svc.get_by_product(po.product_name).quantity or 0) + actual_delivery
                )))

                po.quantity_delivered += actual_delivery
                po.status = "partial"
                po.actual_delivery = self.current_date

                events.append({
                    "type": "po_partial_delivery",
                    "po_id": po.id,
                    "product": po.product_name,
                    "delivered": actual_delivery,
                    "expected": int(po.quantity_ordered - po.quantity_delivered + actual_delivery)
                })
            else:
                # Full delivery
                remaining = float(po.quantity_ordered - po.quantity_delivered)

                inv_svc = InventoryService(self.db)
                inv_svc.adjust(po.product_name, Decimal(str(
                    float(inv_svc.get_by_product(po.product_name).quantity or 0) + remaining
                )))

                po.quantity_delivered = po.quantity_ordered
                po.status = "delivered"
                po.actual_delivery = self.current_date

                events.append({
                    "type": "po_arrived",
                    "po_id": po.id,
                    "product": po.product_name,
                    "quantity": int(remaining)
                })

        return events

    def _generate_demand(self) -> List[Dict]:
        """Generate new manufacturing orders based on simple random distribution (1-3 per day)."""
        events = []

        from app.models.order import ManufacturingOrder
        from app.models.product import ProductModel

        # Simple random distribution: 1-3 new orders per day
        num_new_orders = random.randint(1, 3)
        total_orders = 0

        # Get available product models to choose from
        product_models = self.db.query(ProductModel).all()
        if not product_models:
            return events

        for _ in range(num_new_orders):
            model = random.choice(product_models)
            # Random quantity between 5 and 20
            quantity = random.randint(5, 20)

            order = ManufacturingOrder(
                product_model=model.id,
                quantity_needed=Decimal(str(quantity)),
                quantity_produced=Decimal("0"),
                status="pending",
                created_date=self.current_date
            )
            self.db.add(order)
            total_orders += 1
            events.append({
                "type": "demand_generated",
                "model": model.id,
                "quantity": quantity
            })

        self.db.commit()

        if total_orders > 0:
            events.insert(0, {
                "type": "demand_batch",
                "total_orders": total_orders
            })

        return events

    def _process_manufacturing_orders(self) -> List[Dict]:
        """Process manufacturing orders within daily capacity."""
        events = []
        capacity_per_day = float(self._capacity_per_day)
        produced_today = 0.0

        from app.services.order_service import OrderService
        order_svc = OrderService(self.db)

        # Get released orders
        released_orders = self.db.query(ManufacturingOrder).filter(
            ManufacturingOrder.status == "released"
        ).order_by(ManufacturingOrder.created_date.asc()).all()

        for order in released_orders:
            if produced_today >= capacity_per_day:
                break

            # Calculate how much can be produced this day
            remaining_to_produce = float(order.quantity_needed - order.quantity_produced)
            can_produce = min(remaining_to_produce, capacity_per_day - produced_today)

            if can_produce > 0:
                # Call OrderService to handle logic
                order_svc.produce_units(order.id, can_produce, self.current_date)
                produced_today += float(can_produce)

                # Check if order was completed for logging
                self.db.refresh(order)
                if order.status == "completed":
                    events.append({
                        "type": "order_completed",
                        "order_id": order.id,
                        "model": order.product_model,
                        "quantity": int(order.quantity_needed)
                    })

        if produced_today > 0:
            events.insert(0, {
                "type": "production_summary",
                "produced_today": produced_today,
                "capacity_remaining": capacity_per_day - produced_today
            })

        return events

    def _take_inventory_snapshot(self) -> Dict:
        """Take daily inventory snapshot."""
        from app.models.inventory import Inventory

        items = self.db.query(Inventory).all()
        snapshot = {}

        for item in items:
            snapshot[item.product_name] = {
                "quantity": float(item.quantity),
                "reserved": float(item.reserved_quantity),
                "available": float(item.quantity - item.reserved_quantity)
            }

        # Log the event
        event = EventLog(
            event_type="inventory_snapshot",
            event_date=self.current_date,
            details=str(snapshot)
        )
        self.db.add(event)
        self.db.commit()

        return {
            "type": "inventory_snapshot",
            "date": self.current_date.isoformat(),
            "item_count": len(items)
        }

    def get_status(self) -> Dict:
        """Get current simulation status."""
        pending_count = self.db.query(ManufacturingOrder).filter(
            ManufacturingOrder.status.in_(["pending", "released"])
        ).count()

        return {
            "current_day": self.current_day,
            "current_date": self.current_date.isoformat(),
            "sim_start_date": self.settings.SIMULATION_START_DATE,
            "pending_orders_count": pending_count,
            "capacity_per_day": self._capacity_per_day
        }

    def update_demand_params(self, params: Dict) -> None:
        """Update demand parameters and persist to DB."""
        import json as _json
        from app.models.simulation import SimulationState
        self._demand_params = params
        state = self.db.query(SimulationState).first()
        if state:
            state.demand_params = _json.dumps(params)
            self.db.commit()

    def update_capacity(self, capacity_per_day: int) -> None:
        """Update daily capacity and persist to DB."""
        from app.models.simulation import SimulationState
        self._capacity_per_day = capacity_per_day
        state = self.db.query(SimulationState).first()
        if state:
            state.capacity_per_day = capacity_per_day
            self.db.commit()

    def get_demand_params(self) -> Dict:
        """Get current demand parameters."""
        return self._demand_params or {
            "P3D-Classic": {"mean": 8, "variance": 3},
            "P3D-Pro": {"mean": 5, "variance": 2}
        }
