"""Supplier definitions."""

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from app.db import Base


class Supplier(Base):
    """Represents a supplier of materials."""

    __tablename__ = "suppliers"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    lead_time_days = Column(Integer, nullable=False, default=3)

    # Relationships
    products = relationship("SupplierProduct", back_populates="supplier", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Supplier(id={self.id}, name={self.name}, lead_time={self.lead_time_days}days)>"
