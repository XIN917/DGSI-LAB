"""Purchase Order and Supplier models."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Supplier(Base):
    """Supplier model."""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)

    # Relationships
    products = relationship("SupplierProduct", back_populates="supplier", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Supplier(id={self.id}, name='{self.name}', lead_time={self.lead_time_days})>"


class SupplierProduct(Base):
    """Product offered by a supplier with pricing tiers."""
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    product_name = Column(String(100), nullable=False)  # Matches material_name in BOM
    base_unit_cost = Column(Numeric(10, 2), nullable=False)
    packaging_unit = Column(String(50), nullable=True)  # e.g., "pallet", "box"
    packaging_qty = Column(Integer, nullable=True)  # Units per package
    discount_tiers = Column(String(500), nullable=True)  # JSON string: [{"min_qty": 1000, "discount_pct": 10}]

    # Relationships
    supplier = relationship("Supplier", back_populates="products")

    def __repr__(self):
        return f"<SupplierProduct(supplier_id={self.supplier_id}, product='{self.product_name}', cost={self.base_unit_cost})>"


class PurchaseOrder(Base):
    """Purchase order for ordering materials from suppliers."""
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    product_name = Column(String(100), nullable=False)
    quantity_ordered = Column(Numeric(10, 2), nullable=False)
    quantity_delivered = Column(Numeric(10, 2), default=0)
    unit_cost = Column(Numeric(10, 2), nullable=False)
    order_date = Column(DateTime(timezone=True), nullable=False)
    expected_delivery = Column(DateTime(timezone=True), nullable=False)
    actual_delivery = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), default="pending")  # pending, partial, delivered, cancelled

    def __repr__(self):
        return f"<PurchaseOrder(id={self.id}, supplier_id={self.supplier_id}, product='{self.product_name}', status='{self.status}')>"
