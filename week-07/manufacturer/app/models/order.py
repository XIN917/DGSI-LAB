"""Manufacturing Order model."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from app.core.database import Base


class ManufacturingOrder(Base):
    """Manufacturing order for producing printers."""
    __tablename__ = "manufacturing_orders"

    id = Column(Integer, primary_key=True, index=True)
    product_model = Column(String(50), ForeignKey("product_models.id"), nullable=False)
    quantity_needed = Column(Numeric(10, 2), nullable=False)
    quantity_produced = Column(Numeric(10, 2), default=0)
    status = Column(String(30), default="pending")  # pending, released, waiting_materials, completed, failed
    created_date = Column(DateTime(timezone=True), nullable=False)
    started_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<ManufacturingOrder(id={self.id}, model='{self.product_model}', qty={self.quantity_needed}, status='{self.status}')>"
