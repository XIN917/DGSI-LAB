"""Production Engine - handles production capacity and order completion."""

from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models import (
    ManufacturingOrder, OrderStatus, PrinterModel
)
from app.services.event_logger import EventLogger


class ProductionEngine:
    """Manages production capacity and processes completed orders."""

    def __init__(self):
        self.production_queue: List[str] = []  # Order IDs waiting for capacity

    def get_available_capacity(
        self, db: Session, current_day: int
    ) -> Dict[str, int]:
        """
        Get available production capacity per model for the current day.

        Args:
            db: Database session
            current_day: Current simulation day

        Returns:
            Dict mapping printer_model_id to available capacity
        """
        models = db.query(PrinterModel).all()

        capacity: Dict[str, int] = {}
        for model in models:
            capacity[model.id] = model.daily_capacity

        return capacity

    def get_orders_in_progress(self, db: Session, current_day: int) -> List[ManufacturingOrder]:
        """
        Get all orders that are currently in production (RELEASED or PARTIAL but not COMPLETED).

        Args:
            db: Database session
            current_day: Current simulation day

        Returns:
            List of orders in progress
        """
        return (
            db.query(ManufacturingOrder)
            .filter(ManufacturingOrder.status.in_([OrderStatus.RELEASED, OrderStatus.PARTIAL]))
            .all()
        )

    def process_production(self, db: Session, current_day: int, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process production for the current day.

        This simulates completing orders that have been released or are partially complete.
        Orders are processed in FIFO order.

        Args:
            db: Database session
            current_day: Current simulation day
            config: Optional configuration override

        Returns:
            Results of production processing
        """
        results = {
            "day": current_day,
            "orders_completed": [],
            "orders_partial": [],
            "capacity_used": {},
            "total_produced": 0,
        }

        # Get released or partial orders
        orders_in_progress = self.get_orders_in_progress(db, current_day)

        if not orders_in_progress:
            db.commit()
            return results

        # Calculate total capacity available
        available_capacity = self.get_available_capacity(db, current_day)
        total_capacity = sum(available_capacity.values())

        # Sort by created_day (FIFO)
        orders_in_progress.sort(key=lambda o: (o.created_day, o.released_day or 0))

        # Complete orders until capacity is exhausted
        total_produced = 0
        for order in orders_in_progress:
            if total_produced >= total_capacity:
                break

            # Check if we have capacity for this model
            model_capacity = available_capacity.get(order.printer_model_id, 0)

            # Calculate how many we can produce today
            remaining_capacity = model_capacity - results["capacity_used"].get(order.printer_model_id, 0)

            if remaining_capacity <= 0:
                continue

            # Remaining quantity needed for this order
            remaining_order_qty = order.quantity - order.completed_quantity

            # Produce up to remaining quantity
            qty_to_produce = min(remaining_order_qty, remaining_capacity)

            if qty_to_produce <= 0:
                continue

            # Update order progress
            order.completed_quantity += qty_to_produce

            # Update capacity tracking
            results["capacity_used"][order.printer_model_id] = (
                results["capacity_used"].get(order.printer_model_id, 0) + qty_to_produce
            )
            total_produced += qty_to_produce

            # Update status based on completion
            if order.completed_quantity >= order.quantity:
                order.status = OrderStatus.COMPLETED
                order.completed_day = current_day
                results["orders_completed"].append({
                    "order_id": order.id,
                    "model": order.printer_model_id,
                    "quantity": order.quantity,
                })

                # Log completion event
                EventLogger.log_order_completed(
                    db, current_day, order.id, order.printer_model_id, order.quantity
                )
            else:
                order.status = OrderStatus.PARTIAL
                results["orders_partial"].append({
                    "order_id": order.id,
                    "model": order.printer_model_id,
                    "progress": f"{order.completed_quantity}/{order.quantity}",
                })

        db.commit()

        results["total_produced"] = total_produced
        return results

    def get_production_statistics(
        self, db: Session, current_day: int
    ) -> Dict[str, Any]:
        """
        Get current production statistics.

        Args:
            db: Database session
            current_day: Current simulation day

        Returns:
            Production statistics
        """
        # Count orders by status
        pending_count = db.query(ManufacturingOrder).filter(
            ManufacturingOrder.status == OrderStatus.PENDING
        ).count()

        released_count = db.query(ManufacturingOrder).filter(
            ManufacturingOrder.status.in_([OrderStatus.RELEASED, OrderStatus.PARTIAL])
        ).count()

        completed_today = db.query(ManufacturingOrder).filter(
            ManufacturingOrder.status == OrderStatus.COMPLETED,
            ManufacturingOrder.completed_day == current_day
        ).count()

        # Total quantity in queue
        queue_quantity = sum(
            o.quantity for o in db.query(ManufacturingOrder).filter(
                ManufacturingOrder.status.in_([OrderStatus.PENDING, OrderStatus.RELEASED])
            ).all()
        )

        # Get capacity info
        capacity = self.get_available_capacity(db, current_day)

        return {
            "pending_orders": pending_count,
            "released_orders": released_count,
            "completed_today": completed_today,
            "queue_quantity": queue_quantity,
            "daily_capacity": capacity,
        }


# Global instance
production_engine = ProductionEngine()


def get_production_engine() -> ProductionEngine:
    """Get the global production engine."""
    return production_engine
