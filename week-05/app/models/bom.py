"""Bill of Materials (BOM) definitions."""

from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base


class BOMItem(Base):
    """Represents a material requirement for a printer model."""

    __tablename__ = "bom_items"

    id = Column(String(50), primary_key=True)
    printer_model_id = Column(String(50), ForeignKey("printer_models.id"), nullable=False)
    material_type = Column(String(50), nullable=False)
    quantity_per_unit = Column(Float, nullable=False, default=1.0)

    # Relationship
    printer_model = relationship("PrinterModel", backref="bom_items")

    def __repr__(self):
        return f"<BOMItem(printer={self.printer_model_id}, material={self.material_type}, qty={self.quantity_per_unit})>"
