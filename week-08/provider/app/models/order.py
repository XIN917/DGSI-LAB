from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from app.core.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    buyer = Column(String(100), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    placed_day = Column(Integer, nullable=False)
    expected_delivery_day = Column(Integer, nullable=False)
    shipped_day = Column(Integer)
    delivered_day = Column(Integer)
    status = Column(String(50), nullable=False) # PENDING, CONFIRMED, SHIPPED, DELIVERED, REJECTED, CANCELLED
