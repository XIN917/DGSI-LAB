from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    lead_time_days = Column(Integer, nullable=False)

    pricing_tiers = relationship("PricingTier", back_populates="product", cascade="all, delete-orphan")
    stock = relationship("Stock", back_populates="product", uselist=False, cascade="all, delete-orphan")

class PricingTier(Base):
    __tablename__ = "pricing_tiers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    min_quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)

    product = relationship("Product", back_populates="pricing_tiers")

class Stock(Base):
    __tablename__ = "stock"

    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    quantity = Column(Integer, nullable=False)

    product = relationship("Product", back_populates="stock")
