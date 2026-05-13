"""Printer Model definitions."""

from sqlalchemy import Column, String, Integer, Float
from app.db import Base


class PrinterModel(Base):
    """Represents a 3D printer model that can be manufactured."""

    __tablename__ = "printer_models"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    assembly_time_hours = Column(Integer, nullable=False, default=4)
    daily_capacity = Column(Integer, nullable=False, default=10)

    def __repr__(self):
        return f"<PrinterModel(id={self.id}, name={self.name})>"
