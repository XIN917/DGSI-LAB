"""Inventory Log definitions."""

from sqlalchemy import Column, String, Float, Integer
from app.db import Base


class InventoryLog(Base):
    """Tracks current inventory levels and warehouse capacity."""

    __tablename__ = "inventory_log"

    id = Column(String(50), primary_key=True)
    material_type = Column(String(50), nullable=False, unique=True)
    current_quantity = Column(Float, nullable=False, default=0.0)
    warehouse_capacity = Column(Integer, nullable=False, default=500)

    def __repr__(self):
        return f"<InventoryLog(material={self.material_type}, quantity={self.current_quantity})>"
