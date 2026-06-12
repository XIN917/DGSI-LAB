"""Manufacturing order service."""
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.order import ManufacturingOrder
from app.models.product import ProductModel, BOMItem
from app.models.inventory import Inventory


class OrderService:
    """Service for managing manufacturing orders."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[ManufacturingOrder]:
        """Get all manufacturing orders."""
        return self.db.query(ManufacturingOrder).order_by(
            ManufacturingOrder.created_date.desc()
        ).all()

    def get_pending(self) -> List[ManufacturingOrder]:
        """Get pending orders."""
        return self.db.query(ManufacturingOrder).filter(
            ManufacturingOrder.status == "pending"
        ).all()

    def get_by_id(self, order_id: int) -> Optional[ManufacturingOrder]:
        """Get order by ID."""
        return self.db.query(ManufacturingOrder).filter(
            ManufacturingOrder.id == order_id
        ).first()

    def create(self, product_model: str, quantity: Decimal, created_date: datetime) -> ManufacturingOrder:
        """Create a new manufacturing order."""
        order = ManufacturingOrder(
            product_model=product_model,
            quantity_needed=quantity,
            quantity_produced=Decimal("0"),
            status="pending",
            created_date=created_date
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def calculate_bom_requirements(self, order: ManufacturingOrder) -> Dict:
        """Calculate materials required for an order based on BOM."""
        model = self.db.query(ProductModel).filter(
            ProductModel.id == order.product_model
        ).first()

        if not model:
            return {}

        bom_items = self.db.query(BOMItem).filter(
            BOMItem.model_id == order.product_model
        ).all()

        requirements = {}
        qty_needed = float(order.quantity_needed)

        for item in bom_items:
            required = float(item.quantity_required) * qty_needed
            inventory = self.db.query(Inventory).filter(
                Inventory.product_name == item.material_name
            ).first()

            available = float(inventory.quantity - inventory.reserved_quantity) if inventory else 0

            requirements[item.material_name] = {
                "required": required,
                "available": available,
                "sufficient": available >= required,
                "shortage": max(0, required - available)
            }

        return requirements

    def can_release(self, order: ManufacturingOrder) -> Tuple[bool, List[str]]:
        """Check if order can be released (has all required materials)."""
        requirements = self.calculate_bom_requirements(order)
        missing = [
            mat for mat, req in requirements.items()
            if not req["sufficient"]
        ]
        return len(missing) == 0, missing

    def release(self, order_id: int) -> Tuple[bool, Optional[str]]:
        """Release order to production (reserves materials)."""
        from app.services.inventory_service import InventoryService

        order = self.get_by_id(order_id)
        if not order:
            return False, "Order not found"

        if order.status != "pending":
            return False, f"Order already in {order.status} status"

        can, missing = self.can_release(order)
        if not can:
            order.status = "waiting_materials"
            self.db.commit()
            return False, f"Missing materials: {', '.join(missing)}"

        bom_reqs = self.calculate_bom_requirements(order)
        inventory_svc = InventoryService(self.db)

        for material, req in bom_reqs.items():
            success = inventory_svc.reserve(material, Decimal(str(req["required"])))
            if not success:
                order.status = "waiting_materials"
                self.db.commit()
                return False, f"Failed to reserve {material}"

        order.status = "released"
        order.started_date = datetime.utcnow()
        self.db.commit()
        return True, None

    def produce_units(self, order_id: int, quantity: float, current_date: datetime.date) -> bool:
        """Produce a specific quantity of units for an order."""
        from app.services.inventory_service import InventoryService
        
        order = self.get_by_id(order_id)
        if not order or order.status != "released":
            return False

        # Update production quantity
        order.quantity_produced += Decimal(str(quantity))

        # Consume materials from reserved stock
        inv_svc = InventoryService(self.db)
        # Calculate requirements per unit
        bom_items = self.db.query(BOMItem).filter(BOMItem.model_id == order.product_model).all()
        
        for item in bom_items:
            total_consumed = Decimal(str(float(item.quantity_required) * quantity))
            inv_svc.consume(item.material_name, total_consumed)

        # Check for completion
        if float(order.quantity_produced) >= float(order.quantity_needed):
            order.status = "completed"
            order.completed_date = current_date

        self.db.commit()
        return True

    def cancel(self, order_id: int) -> bool:
        """Cancel order and release reserved materials."""
        from app.services.inventory_service import InventoryService

        order = self.get_by_id(order_id)
        if not order or order.status == "completed":
            return False

        inventory_svc = InventoryService(self.db)
        bom_reqs = self.calculate_bom_requirements(order)

        for material, req in bom_reqs.items():
            inventory_svc.release_reservation(material, Decimal(str(req["required"])))

        order.status = "cancelled"
        self.db.commit()
        return True
