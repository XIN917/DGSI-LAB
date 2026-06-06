from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base


class ProviderMetrics(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sim_day = Column(Integer, nullable=False, index=True)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String, nullable=False)
    stock_quantity = Column(Integer, nullable=False)
    price_tier1 = Column(Float, nullable=True)   # lowest min_quantity tier
    orders_pending = Column(Integer, nullable=False, default=0)
    orders_shipped = Column(Integer, nullable=False, default=0)
    orders_delivered = Column(Integer, nullable=False, default=0)
