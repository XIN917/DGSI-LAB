"""Product model definitions."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProductModel(Base):
    """Product model (printer models like P3D-Classic, P3D-Pro)."""
    __tablename__ = "product_models"

    id = Column(String(50), primary_key=True, index=True)  # e.g., "P3D-Classic"
    name = Column(String(100), nullable=False)
    assembly_time_days = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    bom_items = relationship("BOMItem", back_populates="product_model", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProductModel(id='{self.id}', name='{self.name}')>"


class BOMItem(Base):
    """Bill of Materials item for a product model."""
    __tablename__ = "bom_items"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(String(50), ForeignKey("product_models.id"), nullable=False)
    material_name = Column(String(100), nullable=False)  # e.g., "kit_piezas", "pcb"
    quantity_required = Column(Numeric(10, 2), nullable=False)
    pcb_ref = Column(String(50), nullable=True)  # Optional reference like "CTRL-V2"

    # Relationships
    product_model = relationship("ProductModel", back_populates="bom_items")

    def __repr__(self):
        return f"<BOMItem(model_id='{self.model_id}', material='{self.material_name}', qty={self.quantity_required})>"
