"""Supplier Product definitions."""

from sqlalchemy import Column, String, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base


class SupplierProduct(Base):
    """Represents a product offered by a supplier."""

    __tablename__ = "supplier_products"

    id = Column(String(50), primary_key=True)
    supplier_id = Column(String(50), ForeignKey("suppliers.id"), nullable=False)
    material_type = Column(String(50), nullable=False)
    price_per_unit = Column(Float, nullable=False)
    min_order_qty = Column(Integer, nullable=False, default=1)
    packaging = Column(String(100), nullable=True)

    # Relationship
    supplier = relationship("Supplier", back_populates="products")

    def __repr__(self):
        return f"<SupplierProduct(supplier={self.supplier_id}, material={self.material_type}, price={self.price_per_unit})>"
