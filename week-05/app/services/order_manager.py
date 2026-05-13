"""Order Manager - handles manufacturing order lifecycle."""

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import (
    ManufacturingOrder, OrderStatus, BOMItem, InventoryLog
)
from app.services.event_logger import EventLogger


class OrderManager:
    """Manages manufacturing orders - creation, release, completion."""

    def get_order_material_requirements(
        self, db: Session, order: ManufacturingOrder
    ) -> Dict[str, float]:
        """
        Calculate total material requirements for an order.

        Args:
            db: Database session
            order: The manufacturing order

        Returns:
            Dict mapping material_type to required quantity
        """
        bom_items = (
            db.query(BOMItem)
            .filter(BOMItem.printer_model_id == order.printer_model_id)
            .all()
        )

        requirements: Dict[str, float] = {}
        for item in bom_items:
            requirements[item.material_type] = item.quantity_per_unit * order.quantity

        return requirements

    def check_material_availability(
        self, db: Session, requirements: Dict[str, float]
    ) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
        """
        Check if inventory has sufficient materials.

        Args:
            db: Database session
            requirements: Dict of material_type -> required quantity

        Returns:
            Tuple of (is_available, shortage_details)
            shortage_details contains info about each shortage
        """
        is_available = True
        shortage_details: Dict[str, Dict[str, Any]] = {}

        for material_type, required_qty in requirements.items():
            inv = db.query(InventoryLog).filter(
                InventoryLog.material_type == material_type
            ).first()

            current_stock = inv.current_quantity if inv else 0.0

            if current_stock < required_qty:
                is_available = False
                shortage_details[material_type] = {
                    "required": required_qty,
                    "available": current_stock,
                    "shortage": required_qty - current_stock,
                }

        return is_available, shortage_details

    def can_release_order(
        self, db: Session, order_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if an order can be released (materials available).

        Args:
            db: Database session
            order_id: Order ID to check

        Returns:
            Tuple of (can_release, error_info)
        """
        order = db.query(ManufacturingOrder).filter(
            ManufacturingOrder.id == order_id
        ).first()

        if not order:
            return False, {"error": "Order not found"}

        if order.status != OrderStatus.PENDING:
            return False, {"error": f"Order is not PENDING (current status: {order.status.value})"}

        requirements = self.get_order_material_requirements(db, order)
        is_available, shortage_details = self.check_material_availability(db, requirements)

        if not is_available:
            return False, {
                "error": "Insufficient materials",
                "shortages": shortage_details,
            }

        return True, None

    def release_order(self, db: Session, order_id: str, released_day: int) -> Dict[str, Any]:
        """
        Release an order to production - consumes materials.

        Args:
            db: Database session
            order_id: Order ID to release
            released_day: Current simulation day

        Returns:
            Result dict with success status and details
        """
        # Check if order can be released
        can_release, error_info = self.can_release_order(db, order_id)

        if not can_release:
            return {"success": False, "error": error_info}

        order = db.query(ManufacturingOrder).filter(
            ManufacturingOrder.id == order_id
        ).first()

        # Get material requirements
        requirements = self.get_order_material_requirements(db, order)

        # Consume materials from inventory
        consumed_materials = []
        for material_type, qty_needed in requirements.items():
            inv = db.query(InventoryLog).filter(
                InventoryLog.material_type == material_type
            ).first()

            if inv:
                old_qty = inv.current_quantity
                inv.current_quantity -= qty_needed
                consumed_materials.append({
                    "material": material_type,
                    "quantity": qty_needed,
                    "remaining": inv.current_quantity,
                })

                # Log consumption event
                EventLogger.log_material_consumption(
                    db, released_day, order_id, material_type, qty_needed
                )

        # Update order status
        order.status = OrderStatus.RELEASED
        order.released_day = released_day

        # Commit changes
        db.commit()

        # Log order release event
        EventLogger.log_order_released(
            db, released_day, order_id, order.printer_model_id, order.quantity
        )

        return {
            "success": True,
            "order_id": order_id,
            "status": "RELEASED",
            "consumed_materials": consumed_materials,
        }

    def complete_order(self, db: Session, order_id: str, completed_day: int) -> Dict[str, Any]:
        """
        Mark an order as completed.

        Args:
            db: Database session
            order_id: Order ID to complete
            completed_day: Current simulation day

        Returns:
            Result dict with success status
        """
        order = db.query(ManufacturingOrder).filter(
            ManufacturingOrder.id == order_id
        ).first()

        if not order:
            return {"success": False, "error": "Order not found"}

        if order.status != OrderStatus.RELEASED:
            return {
                "success": False,
                "error": f"Order must be RELEASED to complete (current: {order.status.value})",
            }

        order.status = OrderStatus.COMPLETED
        order.completed_day = completed_day
        db.commit()

        # Log completion event
        EventLogger.log_order_completed(
            db, completed_day, order_id, order.printer_model_id, order.quantity
        )

        return {
            "success": True,
            "order_id": order_id,
            "status": "COMPLETED",
        }

    def cancel_order(self, db: Session, order_id: str, day: int = 1) -> Dict[str, Any]:
        """
        Cancel a pending order.

        Args:
            db: Database session
            order_id: Order ID to cancel
            day: Current simulation day for event logging

        Returns:
            Result dict with success status
        """
        order = db.query(ManufacturingOrder).filter(
            ManufacturingOrder.id == order_id
        ).first()

        if not order:
            return {"success": False, "error": "Order not found"}

        if order.status != OrderStatus.PENDING:
            return {
                "success": False,
                "error": f"Only PENDING orders can be cancelled (current: {order.status.value})",
            }

        order.status = OrderStatus.CANCELLED
        db.commit()

        # Log cancellation event
        EventLogger.log_event(
            db=db,
            day=day,
            event_type="ORDER_CANCELLED",
            category="DEMAND",
            description=f"Order {order_id} cancelled",
            details={"order_id": order_id},
        )

        return {"success": True, "order_id": order_id, "status": "CANCELLED"}

    def get_pending_material_shortages(
        self, db: Session
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate total material shortages for all pending/released orders.

        Args:
            db: Database session

        Returns:
            Dict of material_type -> shortage info
        """
        # Get all pending and released orders
        orders = (
            db.query(ManufacturingOrder)
            .filter(ManufacturingOrder.status.in_([OrderStatus.PENDING, OrderStatus.RELEASED]))
            .all()
        )

        # Aggregate requirements
        total_requirements: Dict[str, float] = {}
        for order in orders:
            reqs = self.get_order_material_requirements(db, order)
            for material, qty in reqs.items():
                total_requirements[material] = total_requirements.get(material, 0) + qty

        # Compare with inventory
        shortages: Dict[str, Dict[str, float]] = {}
        for material, required in total_requirements.items():
            inv = db.query(InventoryLog).filter(
                InventoryLog.material_type == material
            ).first()

            current = inv.current_quantity if inv else 0.0
            if current < required:
                shortages[material] = {
                    "required": required,
                    "available": current,
                    "shortage": required - current,
                }

        return shortages


# Global instance
order_manager = OrderManager()


def get_order_manager() -> OrderManager:
    """Get the global order manager."""
    return order_manager
