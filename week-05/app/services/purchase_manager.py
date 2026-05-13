"""Purchase Manager - handles purchase orders and supplier interactions."""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models import (
    PurchaseOrder, PurchaseOrderStatus, Supplier, SupplierProduct
)
from app.services.event_logger import EventLogger


class PurchaseManager:
    """Manages purchase orders from suppliers."""

    def __init__(self):
        self.default_lead_time = 3  # days

    def get_suppliers(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get all registered suppliers.

        Args:
            db: Database session

        Returns:
            List of supplier info dicts
        """
        suppliers = db.query(Supplier).all()

        return [
            {
                "id": s.id,
                "name": s.name,
                "lead_time_days": s.lead_time_days,
            }
            for s in suppliers
        ]

    def get_supplier_products(
        self, db: Session, supplier_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get products available from a specific supplier.

        Args:
            db: Database session
            supplier_id: Supplier ID

        Returns:
            List of product info dicts
        """
        products = (
            db.query(SupplierProduct)
            .filter(SupplierProduct.supplier_id == supplier_id)
            .all()
        )

        return [
            {
                "id": p.id,
                "material_type": p.material_type,
                "price_per_unit": p.price_per_unit,
                "min_order_qty": p.min_order_qty,
                "packaging": p.packaging,
            }
            for p in products
        ]

    def calculate_delivery_date(
        self, order_day: int, supplier_id: str, db: Session
    ) -> int:
        """
        Calculate expected delivery date based on supplier lead time.

        Args:
            order_day: Day the order is placed
            supplier_id: Supplier ID
            db: Database session

        Returns:
            Expected delivery day
        """
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()

        if supplier:
            return order_day + supplier.lead_time_days
        return order_day + self.default_lead_time

    def create_purchase_order(
        self,
        db: Session,
        po_id: str,
        supplier_id: str,
        material_type: str,
        quantity: float,
        order_day: int,
    ) -> Dict[str, Any]:
        """
        Create a new purchase order.

        Args:
            db: Database session
            po_id: Unique PO ID
            supplier_id: Supplier ID
            material_type: Material type to purchase
            quantity: Quantity to order
            order_day: Current simulation day

        Returns:
            Result dict with success status and PO details
        """
        # Validate supplier exists
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            return {"success": False, "error": "Supplier not found"}

        # Validate product exists
        product = db.query(SupplierProduct).filter(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.material_type == material_type
        ).first()

        if not product:
            return {"success": False, "error": "Product not available from this supplier"}

        # Check minimum order quantity
        if quantity < product.min_order_qty:
            return {
                "success": False,
                "error": f"Quantity below minimum order quantity ({product.min_order_qty})",
            }

        # Calculate delivery date
        expected_arrival = self.calculate_delivery_date(order_day, supplier_id, db)

        # Create the PO
        po = PurchaseOrder(
            id=po_id,
            supplier_id=supplier_id,
            material_type=material_type,
            quantity=quantity,
            order_day=order_day,
            expected_arrival=expected_arrival,
            status=PurchaseOrderStatus.PENDING,
        )

        db.add(po)
        db.commit()

        # Log creation event
        EventLogger.log_purchase_order_created(
            db, order_day, po_id, supplier_id, material_type, quantity, expected_arrival
        )

        return {
            "success": True,
            "purchase_order": {
                "id": po_id,
                "supplier_id": supplier_id,
                "material_type": material_type,
                "quantity": quantity,
                "order_day": order_day,
                "expected_arrival": expected_arrival,
                "status": PurchaseOrderStatus.PENDING.value,
            },
        }

    def get_purchase_orders(
        self, db: Session, status: Optional[PurchaseOrderStatus] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all purchase orders, optionally filtered by status.

        Args:
            db: Database session
            status: Optional status filter

        Returns:
            List of purchase order info dicts
        """
        query = db.query(PurchaseOrder)

        if status:
            query = query.filter(PurchaseOrder.status == status)

        orders = query.all()

        return [
            {
                "id": o.id,
                "supplier_id": o.supplier_id,
                "material_type": o.material_type,
                "quantity": o.quantity,
                "order_day": o.order_day,
                "expected_arrival": o.expected_arrival,
                "actual_arrival": o.actual_arrival,
                "status": o.status.value,
            }
            for o in orders
        ]

    def get_pending_purchase_orders(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get all pending purchase orders.

        Args:
            db: Database session

        Returns:
            List of pending POs
        """
        return self.get_purchase_orders(db, PurchaseOrderStatus.PENDING)

    def cancel_purchase_order(
        self, db: Session, po_id: str, day: int
    ) -> Dict[str, Any]:
        """
        Cancel a pending purchase order.

        Args:
            db: Database session
            po_id: Purchase order ID
            day: Current simulation day

        Returns:
            Result dict with success status
        """
        po = db.query(PurchaseOrder).filter(
            PurchaseOrder.id == po_id
        ).first()

        if not po:
            return {"success": False, "error": "Purchase order not found"}

        if po.status != PurchaseOrderStatus.PENDING:
            return {
                "success": False,
                "error": f"Only PENDING orders can be cancelled (current: {po.status.value})",
            }

        po.status = PurchaseOrderStatus.CANCELLED
        db.commit()

        # Log cancellation event
        EventLogger.log_purchase_order_cancelled(db, po_id, day)

        return {"success": True, "purchase_order_id": po_id, "status": "CANCELLED"}

    def estimate_total_cost(
        self, db: Session, supplier_id: str, material_type: str, quantity: float
    ) -> Dict[str, Any]:
        """
        Estimate total cost for a potential purchase order.

        Args:
            db: Database session
            supplier_id: Supplier ID
            material_type: Material type
            quantity: Quantity to order

        Returns:
            Cost breakdown
        """
        product = db.query(SupplierProduct).filter(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.material_type == material_type
        ).first()

        if not product:
            return {"success": False, "error": "Product not found"}

        return {
            "success": True,
            "material_type": material_type,
            "quantity": quantity,
            "price_per_unit": product.price_per_unit,
            "total_cost": product.price_per_unit * quantity,
            "supplier_id": supplier_id,
        }


# Global instance
purchase_manager = PurchaseManager()


def get_purchase_manager() -> PurchaseManager:
    """Get the global purchase manager."""
    return purchase_manager
