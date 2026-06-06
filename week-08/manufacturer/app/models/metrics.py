from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base


class ManufacturerMetrics(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sim_day = Column(Integer, nullable=False, index=True)
    model_name = Column(String, nullable=False)
    finished_stock = Column(Integer, nullable=False, default=0)
    wholesale_price = Column(Float, nullable=True)
    sales_orders_pending = Column(Integer, nullable=False, default=0)
    sales_orders_completed = Column(Integer, nullable=False, default=0)
    production_utilisation = Column(Float, nullable=True)  # 0.0–1.0
    parts_stock_json = Column(String, nullable=True)        # JSON: {part_name: qty}
