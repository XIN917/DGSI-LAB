"""Pricing tier model for Provider app."""
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from provider.app.db import Base


class PricingTier(Base):
    __tablename__ = "pricing_tiers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    min_quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "min_quantity": self.min_quantity,
            "unit_price": self.unit_price,
        }