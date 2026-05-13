"""Stock model for Provider app."""
from sqlalchemy import Column, Integer, ForeignKey
from provider.app.db import Base


class Stock(Base):
    __tablename__ = "stock"

    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    quantity = Column(Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "product_id": self.product_id,
            "quantity": self.quantity,
        }