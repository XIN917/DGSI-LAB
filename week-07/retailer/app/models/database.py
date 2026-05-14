from datetime import UTC, datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class OrderStatus(str, Enum):
    pending = "pending"
    fulfilled = "fulfilled"
    backordered = "backordered"
    cancelled = "cancelled"


class CustomerOrderDB(Base):
    __tablename__ = "customer_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    retail_price = Column(Float, nullable=False)
    status = Column(String, nullable=False, default=OrderStatus.pending)
    created_day = Column(Integer, nullable=False)
    fulfilled_day = Column(Integer, nullable=True)
    backorder_date = Column(Integer, nullable=True)
    customer_name = Column(String, nullable=True)
    notes = Column(Text, nullable=True)


class InventoryItemDB(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String, unique=True, nullable=False)
    quantity_on_hand = Column(Integer, nullable=False, default=0)
    quantity_reserved = Column(Integer, nullable=False, default=0)
    retail_price = Column(Float, nullable=False)
    last_cost = Column(Float, nullable=True)


class PurchaseOrderDB(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    manufacturer_po_id = Column(Integer, nullable=True)
    sku = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    wholesale_unit_price = Column(Float, nullable=False)
    retail_unit_price = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="pending")
    placed_day = Column(Integer, nullable=False)
    expected_delivery_day = Column(Integer, nullable=True)
    received_day = Column(Integer, nullable=True)


class EventLogDB(Base):
    __tablename__ = "event_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sim_day = Column(Integer, nullable=False)
    event_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class SimStateDB(Base):
    __tablename__ = "sim_state"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
