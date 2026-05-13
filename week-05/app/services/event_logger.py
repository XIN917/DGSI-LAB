"""Event Logger service for recording simulation events."""

import json
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models import EventLog


class EventLogger:
    """Records all events in the simulation for historical tracking."""

    @staticmethod
    def log_event(
        db: Session,
        day: int,
        event_type: str,
        category: str,
        description: str,
        details: Optional[dict] = None,
        timestamp: float = 0.0,
    ) -> EventLog:
        """
        Log a simulation event.

        Args:
            db: Database session
            day: Simulated day number
            event_type: Type of event (e.g., "ORDER_CREATED", "PRODUCTION_COMPLETED")
            category: Category (DEMAND, PRODUCTION, PURCHASING, INVENTORY, SYSTEM)
            description: Human-readable description
            details: Optional dict with additional event data
            timestamp: Simulated time within day (0.0-24.0)

        Returns:
            The created EventLog record
        """
        event_id = f"evt_{uuid.uuid4().hex[:12]}"

        event = EventLog(
            id=event_id,
            day=day,
            timestamp=timestamp,
            event_type=event_type,
            category=category,
            description=description,
            details=json.dumps(details) if details else None,
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        return event

    @staticmethod
    def log_order_created(db: Session, day: int, order_id: str, model_id: str, quantity: int):
        """Log when a manufacturing order is created."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="ORDER_CREATED",
            category="DEMAND",
            description=f"New order {order_id} created for {quantity}x {model_id}",
            details={"order_id": order_id, "model_id": model_id, "quantity": quantity},
        )

    @staticmethod
    def log_order_released(db: Session, day: int, order_id: str, model_id: str, quantity: int):
        """Log when an order is released to production."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="ORDER_RELEASED",
            category="PRODUCTION",
            description=f"Order {order_id} ({quantity} units) released to production",
            details={"order_id": order_id, "model_id": model_id, "quantity": quantity},
        )

    @staticmethod
    def log_order_completed(db: Session, day: int, order_id: str, model_id: str, quantity: int):
        """Log when an order is completed."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="ORDER_COMPLETED",
            category="PRODUCTION",
            description=f"Order {order_id} completed ({quantity} units of {model_id})",
            details={"order_id": order_id, "model_id": model_id, "quantity": quantity},
        )

    @staticmethod
    def log_order_cancelled(db: Session, day: int, order_id: str):
        """Log when an order is cancelled."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="ORDER_CANCELLED",
            category="DEMAND",
            description=f"Order {order_id} cancelled",
            details={"order_id": order_id},
        )

    @staticmethod
    def log_material_consumption(db: Session, day: int, order_id: str, material: str, quantity: float):
        """Log when materials are consumed for production."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="MATERIAL_CONSUMED",
            category="INVENTORY",
            description=f"Consumed {quantity} {material} for order {order_id}",
            details={"order_id": order_id, "material": material, "quantity": quantity},
        )

    @staticmethod
    def log_inventory_update(db: Session, day: int, material: str, quantity: float, reason: str, new_level: float):
        """Log inventory update (delivery, consumption, etc.)."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="INVENTORY_UPDATE",
            category="INVENTORY",
            description=f"Inventory update: {reason} - {quantity} {material}, new level: {new_level}",
            details={"material": material, "quantity": quantity, "reason": reason, "new_level": new_level},
        )

    @staticmethod
    def log_purchase_order_cancelled(db: Session, po_id: str, day: int):
        """Log when a purchase order is cancelled."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="PURCHASE_ORDER_CANCELLED",
            category="PURCHASING",
            description=f"Purchase order {po_id} cancelled",
            details={"po_id": po_id},
        )

    @staticmethod
    def log_purchase_order_created(db: Session, day: int, po_id: str, supplier_id: str, material: str, quantity: float, lead_time: int):
        """Log when a purchase order is created."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="PURCHASE_ORDER_CREATED",
            category="PURCHASING",
            description=f"PO {po_id} placed with {supplier_id} for {quantity} {material} (arrives day {day + lead_time})",
            details={
                "po_id": po_id,
                "supplier_id": supplier_id,
                "material": material,
                "quantity": quantity,
                "lead_time": lead_time,
                "expected_arrival": day + lead_time,
            },
        )

    @staticmethod
    def log_purchase_delivery(db: Session, day: int, po_id: str, material: str, quantity: float):
        """Log when a purchase order delivery arrives."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="PURCHASE_DELIVERY",
            category="PURCHASING",
            description=f"Delivery arrived: {quantity} {material} from PO {po_id}",
            details={"po_id": po_id, "material": material, "quantity": quantity},
        )

    @staticmethod
    def log_production_started(db: Session, day: int, order_id: str, quantity: int):
        """Log when production starts on an order."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="PRODUCTION_STARTED",
            category="PRODUCTION",
            description=f"Production started on order {order_id} ({quantity} units)",
            details={"order_id": order_id, "quantity": quantity},
        )

    @staticmethod
    def log_production_completed(db: Session, day: int, order_id: str, quantity: int):
        """Log when an order is completed."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="PRODUCTION_COMPLETED",
            category="PRODUCTION",
            description=f"Order {order_id} completed ({quantity} units produced)",
            details={"order_id": order_id, "quantity": quantity},
        )

    @staticmethod
    def log_material_consumed(db: Session, day: int, order_id: str, material: str, quantity: float):
        """Log when materials are consumed for production."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="MATERIAL_CONSUMED",
            category="INVENTORY",
            description=f"Consumed {quantity} {material} for order {order_id}",
            details={"order_id": order_id, "material": material, "quantity": quantity},
        )

    @staticmethod
    def log_inventory_shortage(db: Session, day: int, material: str, needed: float, available: float):
        """Log when there's an inventory shortage."""
        return EventLogger.log_event(
            db=db,
            day=day,
            event_type="INVENTORY_SHORTAGE",
            category="INVENTORY",
            description=f"Shortage: need {needed} {material}, only {available} available",
            details={"material": material, "needed": needed, "available": available, "shortage": needed - available},
        )


# Convenience function
def get_event_logger():
    """Get the event logger instance."""
    return EventLogger()
