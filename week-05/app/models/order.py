"""Manufacturing Order definitions."""

from enum import Enum as PyEnum
from sqlalchemy import Column, String, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.db import Base


class OrderStatus(PyEnum):
    """Status of a manufacturing order."""
    PENDING = "PENDING"
    RELEASED = "RELEASED"
    PARTIAL = "PARTIAL"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ManufacturingOrder(Base):
    """Represents a production order for 3D printers."""

    __tablename__ = "manufacturing_orders"

    id = Column(String(50), primary_key=True)
    printer_model_id = Column(String(50), ForeignKey("printer_models.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    completed_quantity = Column(Integer, nullable=False, default=0)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    created_day = Column(Integer, nullable=False)
    released_day = Column(Integer, nullable=True)
    completed_day = Column(Integer, nullable=True)

    # Relationship
    printer_model = relationship("PrinterModel", backref="orders")

    def __repr__(self):
        return f"<ManufacturingOrder(id={self.id}, model={self.printer_model_id}, qty={self.quantity}, status={self.status.value})>"
