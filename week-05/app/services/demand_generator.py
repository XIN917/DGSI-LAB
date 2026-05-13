"""Demand Generator - creates random manufacturing orders."""

import random
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import ManufacturingOrder, OrderStatus, PrinterModel
from app.services.event_logger import EventLogger


class DemandGenerator:
    """Generates random manufacturing orders based on configurable parameters."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the demand generator.

        Args:
            config: Optional dict with demand generation parameters:
                - mean_orders_per_day: Average number of orders per day (default: 2.0)
                - variance_orders_per_day: Variance in order count (default: 1.0)
                - min_order_quantity: Minimum quantity per order (default: 1)
                - max_order_quantity: Maximum quantity per order (default: 15)
                - order_quantity_mean: Mean order quantity (default: 8)
                - order_quantity_variance: Variance in order quantity (default: 4)
        """
        self.config = config or {}
        self.mean_orders_per_day = self.config.get("mean_orders_per_day", 2.0)
        self.variance_orders_per_day = self.config.get("variance_orders_per_day", 1.0)
        self.min_order_quantity = self.config.get("min_order_quantity", 1)
        self.max_order_quantity = self.config.get("max_order_quantity", 15)
        self.order_quantity_mean = self.config.get("order_quantity_mean", 8)
        self.order_quantity_variance = self.config.get("order_quantity_variance", 4)

    def set_config(self, config: Dict[str, Any]):
        """Update configuration parameters."""
        self.config = config
        self.mean_orders_per_day = config.get("mean_orders_per_day", self.mean_orders_per_day)
        self.variance_orders_per_day = config.get("variance_orders_per_day", self.variance_orders_per_day)
        self.min_order_quantity = config.get("min_order_quantity", self.min_order_quantity)
        self.max_order_quantity = config.get("max_order_quantity", self.max_order_quantity)
        self.order_quantity_mean = config.get("order_quantity_mean", self.order_quantity_mean)
        self.order_quantity_variance = config.get("order_quantity_variance", self.order_quantity_variance)

    def generate_orders_for_day(self, db: Session, day: int, printer_models: list) -> list:
        """
        Generate random manufacturing orders for a given day.

        Args:
            db: Database session
            day: The simulated day number
            printer_models: List of available printer model IDs

        Returns:
            List of created ManufacturingOrder objects
        """
        if not printer_models:
            return []

        # Determine how many orders to generate this day
        # Use Poisson-like distribution around the mean
        num_orders = max(0, int(random.gauss(self.mean_orders_per_day, self.variance_orders_per_day)))

        created_orders = []

        for _ in range(num_orders):
            # Pick a random printer model
            model_id = random.choice(printer_models)

            # Generate order quantity
            quantity = max(
                self.min_order_quantity,
                min(
                    self.max_order_quantity,
                    int(random.gauss(self.order_quantity_mean, self.order_quantity_variance))
                )
            )

            # Create unique order ID
            order_id = f"MO_{day}_{len(created_orders) + 1:03d}"

            # Create the order
            order = ManufacturingOrder(
                id=order_id,
                printer_model_id=model_id,
                quantity=quantity,
                status=OrderStatus.PENDING,
                created_day=day,
            )

            db.add(order)
            db.commit()
            db.refresh(order)

            # Log the event
            EventLogger.log_order_created(db, day, order.id, model_id, quantity)

            created_orders.append(order)

        return created_orders

    def get_statistics(self) -> Dict[str, float]:
        """Return current configuration statistics."""
        return {
            "mean_orders_per_day": self.mean_orders_per_day,
            "variance_orders_per_day": self.variance_orders_per_day,
            "min_order_quantity": self.min_order_quantity,
            "max_order_quantity": self.max_order_quantity,
            "order_quantity_mean": self.order_quantity_mean,
            "order_quantity_variance": self.order_quantity_variance,
        }


# Global instance
demand_generator = DemandGenerator()


def get_demand_generator() -> DemandGenerator:
    """Get the global demand generator instance."""
    return demand_generator
