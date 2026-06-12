"""Inventory model."""
from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Inventory(Base):
    """Inventory model for tracking material quantities."""
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(100), unique=True, nullable=False, index=True)
    quantity = Column(Numeric(10, 2), default=0, nullable=False)
    reserved_quantity = Column(Numeric(10, 2), default=0, nullable=False)  # Reserved for released orders
    max_capacity = Column(Numeric(10, 2), default=250, nullable=False)  # Maximum bin capacity
    unit_type = Column(String(20), default="raw")  # "raw" or "finished"
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def available(self):
        """Get available quantity (not reserved)."""
        return float(self.quantity - self.reserved_quantity)

    def __repr__(self):
        return f"<Inventory(product='{self.product_name}', qty={self.quantity}, reserved={self.reserved_quantity})>"
