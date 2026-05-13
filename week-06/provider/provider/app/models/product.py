"""Product model for Provider app."""
from sqlalchemy import Column, Integer, String, Text
from provider.app.db import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    lead_time_days = Column(Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "lead_time_days": self.lead_time_days,
        }