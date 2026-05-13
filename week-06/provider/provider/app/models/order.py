"""Order model for Provider app."""
from sqlalchemy import Column, Integer, String, Float, DateTime
from provider.app.db import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    buyer = Column(String, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    placed_day = Column(Integer, nullable=False)
    expected_delivery_day = Column(Integer, nullable=False)
    shipped_day = Column(Integer, nullable=True)
    delivered_day = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, confirmed, shipped, delivered

    def to_dict(self):
        return {
            "id": self.id,
            "buyer": self.buyer,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "placed_day": self.placed_day,
            "expected_delivery_day": self.expected_delivery_day,
            "shipped_day": self.shipped_day,
            "delivered_day": self.delivered_day,
            "status": self.status,
        }