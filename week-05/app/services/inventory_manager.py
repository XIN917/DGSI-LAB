"""Inventory Manager - handles inventory levels and material consumption."""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models import InventoryLog, ManufacturingOrder, OrderStatus, BOMItem
from app.services.event_logger import EventLogger


class InventoryManager:
    """Manages inventory levels and shortage detection."""

    def __init__(self):
        self.shortage_threshold = 0.2  # Alert when below 20% of pending needs

    def get_inventory_levels(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get current inventory levels for all materials.

        Args:
            db: Database session

        Returns:
            List of inventory records with current levels
        """
        items = db.query(InventoryLog).all()

        return [
            {
                "material_type": item.material_type,
                "current_quantity": item.current_quantity,
                "warehouse_capacity": item.warehouse_capacity,
            }
            for item in items
        ]

    def get_material_stock(self, db: Session, material_type: str) -> Optional[Dict[str, Any]]:
        """
        Get stock level for a specific material.

        Args:
            db: Database session
            material_type: Material type ID

        Returns:
            Stock info or None if not found
        """
        item = db.query(InventoryLog).filter(
            InventoryLog.material_type == material_type
        ).first()

        if item:
            return {
                "material_type": item.material_type,
                "current_quantity": item.current_quantity,
                "warehouse_capacity": item.warehouse_capacity,
            }
        return None

    def update_stock(
        self, db: Session, material_type: str, quantity_change: float, day: int
    ) -> Dict[str, Any]:
        """
        Update stock level (positive for receive, negative for consume).

        Args:
            db: Database session
            material_type: Material type ID
            quantity_change: Amount to add (positive) or subtract (negative)
            day: Current simulation day

        Returns:
            Result dict with success status and new quantity
        """
        inv = db.query(InventoryLog).filter(
            InventoryLog.material_type == material_type
        ).first()

        if not inv:
            return {"success": False, "error": "Material not found in inventory"}

        old_quantity = inv.current_quantity
        new_quantity = old_quantity + quantity_change

        # Check warehouse capacity
        if new_quantity > inv.warehouse_capacity:
            return {
                "success": False,
                "error": "Exceeds warehouse capacity",
                "old_quantity": old_quantity,
                "requested": quantity_change,
                "capacity": inv.warehouse_capacity,
            }

        inv.current_quantity = new_quantity
        db.commit()

        return {
            "success": True,
            "material_type": material_type,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "change": quantity_change,
        }

    def receive_material(
        self, db: Session, material_type: str, quantity: float, day: int
    ) -> Dict[str, Any]:
        """
        Receive material from a purchase order delivery.

        Args:
            db: Database session
            material_type: Material type ID
            quantity: Quantity received
            day: Current simulation day

        Returns:
            Result dict with success status
        """
        result = self.update_stock(db, material_type, quantity, day)

        if result["success"]:
            # Log delivery event
            EventLogger.log_inventory_update(
                db, day, material_type, quantity, "DELIVERY", result["new_quantity"]
            )
        else:
            # Log shortage/warning event
            EventLogger.log_event(
                db=db,
                day=day,
                event_type="INVENTORY_WARNING",
                category="INVENTORY",
                description=f"Failed to deliver {quantity} units of {material_type}: {result['error']}",
                details={"material": material_type, "quantity": quantity, "reason": result["error"]},
            )

        return result

    def check_warehouse_capacity(self, db: Session) -> Dict[str, Any]:
        """
        Check overall warehouse capacity utilization.

        Args:
            db: Database session

        Returns:
            Capacity usage info
        """
        items = db.query(InventoryLog).all()

        total_used = sum(item.current_quantity for item in items)
        # Warehouse capacity is shared - use max across all items
        capacity = max((item.warehouse_capacity for item in items), default=500)

        return {
            "total_used": total_used,
            "capacity": capacity,
            "utilization_pct": (total_used / capacity * 100) if capacity > 0 else 0,
            "available": capacity - total_used,
        }

    def detect_shortages(
        self, db: Session, order_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect material shortages for pending/released orders.

        Args:
            db: Database session
            order_id: Optional specific order to check

        Returns:
            List of shortage records
        """
        from app.services.order_manager import get_order_manager

        order_mgr = get_order_manager()

        if order_id:
            # Check specific order
            can_release, error_info = order_mgr.can_release_order(db, order_id)
            if not can_release and error_info.get("shortages"):
                return [
                    {
                        "order_id": order_id,
                        "material": mat,
                        **details,
                    }
                    for mat, details in error_info["shortages"].items()
                ]
            return []
        else:
            # Check all pending orders
            shortages = order_mgr.get_pending_material_shortages(db)
            return [
                {"order_id": "ALL", "material": mat, **details}
                for mat, details in shortages.items()
            ]

    def get_low_stock_alerts(
        self, db: Session, threshold_pct: float = None
    ) -> List[Dict[str, Any]]:
        """
        Get alerts for materials running low relative to pending demand.

        Args:
            db: Database session
            threshold_pct: Percentage threshold (default 20%)

        Returns:
            List of low stock alerts
        """
        if threshold_pct is None:
            threshold_pct = self.shortage_threshold * 100

        from app.services.order_manager import get_order_manager

        order_mgr = get_order_manager()

        # Get future requirements from pending/released orders
        future_requirements: Dict[str, float] = {}
        orders = (
            db.query(ManufacturingOrder)
            .filter(ManufacturingOrder.status.in_([OrderStatus.PENDING, OrderStatus.RELEASED]))
            .all()
        )

        for order in orders:
            reqs = order_mgr.get_order_material_requirements(db, order)
            for mat, qty in reqs.items():
                future_requirements[mat] = future_requirements.get(mat, 0) + qty

        alerts = []
        for mat, required in future_requirements.items():
            inv = db.query(InventoryLog).filter(
                InventoryLog.material_type == mat
            ).first()

            if inv and inv.current_quantity < required:
                alerts.append({
                    "material_type": mat,
                    "current_stock": inv.current_quantity,
                    "future_requirement": required,
                    "shortfall": required - inv.current_quantity,
                    "severity": "HIGH" if inv.current_quantity == 0 else "MEDIUM",
                })

        return alerts


# Global instance
inventory_manager = InventoryManager()


def get_inventory_manager() -> InventoryManager:
    """Get the global inventory manager."""
    return inventory_manager
