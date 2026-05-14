"""Inventory management service."""
from decimal import Decimal
from sqlalchemy.orm import Session
from typing import List, Dict, Optional

from app.models.inventory import Inventory


class InventoryService:
    """Service for managing inventory."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Inventory]:
        """Get all inventory items."""
        return self.db.query(Inventory).all()

    def get_by_product(self, product_name: str) -> Optional[Inventory]:
        """Get inventory item by product name."""
        return self.db.query(Inventory).filter(
            Inventory.product_name == product_name
        ).first()

    def get_available(self, product_name: str) -> Decimal:
        """Get available quantity (not reserved)."""
        inv = self.get_by_product(product_name)
        if not inv:
            return Decimal("0")
        return inv.quantity - inv.reserved_quantity

    def reserve(self, product_name: str, quantity: Decimal) -> bool:
        """Reserve materials for an order."""
        inv = self.get_by_product(product_name)
        if not inv:
            return False

        available = inv.quantity - inv.reserved_quantity
        if available < quantity:
            return False

        inv.reserved_quantity += quantity
        self.db.commit()
        return True

    def consume(self, product_name: str, quantity: Decimal) -> bool:
        """Consume materials from inventory."""
        inv = self.get_by_product(product_name)
        if not inv:
            return False

        available = inv.quantity - inv.reserved_quantity
        if available < quantity:
            return False

        inv.quantity -= quantity
        inv.reserved_quantity -= quantity
        self.db.commit()
        return True

    def release_reservation(self, product_name: str, quantity: Decimal) -> bool:
        """Release reserved materials back to available."""
        inv = self.get_by_product(product_name)
        if not inv:
            return False

        if inv.reserved_quantity < quantity:
            return False

        inv.reserved_quantity -= quantity
        self.db.commit()
        return True

    def adjust(self, product_name: str, new_quantity: Decimal) -> Inventory:
        """Manually adjust inventory quantity."""
        inv = self.get_by_product(product_name)
        if inv:
            inv.quantity = new_quantity
        else:
            inv = Inventory(
                product_name=product_name,
                quantity=new_quantity,
                reserved_quantity=Decimal("0"),
                unit_type="raw"
            )
            self.db.add(inv)

        self.db.commit()
        self.db.refresh(inv)
        return inv

    def get_warehouse_usage(self, capacity: int) -> Dict:
        """Get warehouse capacity usage."""
        total_used = sum(float(item.quantity) for item in self.get_all())
        return {
            "used": total_used,
            "capacity": capacity,
            "percentage": (total_used / capacity * 100) if capacity > 0 else 0
        }
