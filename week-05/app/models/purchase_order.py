"""Purchase Order definitions."""

from enum import Enum as PyEnum
from sqlalchemy import Column, String, Float, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.db import Base


class PurchaseOrderStatus(PyEnum):
    """Status of a purchase order."""
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class PurchaseOrder(Base):
    """Represents a purchase order to a supplier."""

    __tablename__ = "purchase_orders"

    id = Column(String(50), primary_key=True)
    supplier_id = Column(String(50), ForeignKey("suppliers.id"), nullable=False)
    material_type = Column(String(50), nullable=False)
    quantity = Column(Float, nullable=False)
    order_day = Column(Integer, nullable=False)
    expected_arrival = Column(Integer, nullable=False)
    actual_arrival = Column(Integer, nullable=True)
    status = Column(Enum(PurchaseOrderStatus), nullable=False, default=PurchaseOrderStatus.PENDING)

    # Relationship
    supplier = relationship("Supplier", backref="purchase_orders")

    def __repr__(self):
        return f"<PurchaseOrder(id={self.id}, supplier={self.supplier_id}, material={self.material_type}, qty={self.quantity})>"
