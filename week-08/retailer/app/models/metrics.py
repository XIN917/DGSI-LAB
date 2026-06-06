from datetime import UTC, datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from app.models.database import Base


class RetailerMetrics(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sim_day = Column(Integer, nullable=False, index=True)
    sku = Column(String, nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)
    retail_price = Column(Float, nullable=False)
    orders_placed = Column(Integer, nullable=False, default=0)
    orders_fulfilled = Column(Integer, nullable=False, default=0)
    orders_backordered = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
