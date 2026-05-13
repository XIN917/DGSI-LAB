"""Material Type definitions."""

from sqlalchemy import Column, String
from app.db import Base


class MaterialType(Base):
    """Represents a type of raw material used in production."""

    __tablename__ = "material_types"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    unit = Column(String(20), nullable=False, default="units")

    def __repr__(self):
        return f"<MaterialType(id={self.id}, name={self.name}, unit={self.unit})>"
