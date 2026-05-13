"""Event Log definitions."""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from app.db import Base


class EventLog(Base):
    """Records all events in the simulation for historical tracking."""

    __tablename__ = "event_log"

    id = Column(String(50), primary_key=True)
    day = Column(Integer, nullable=False)
    timestamp = Column(Float, nullable=False)  # Simulated time within day
    event_type = Column(String(50), nullable=False)  # ORDER_CREATED, ORDER_RELEASED, etc.
    category = Column(String(20), nullable=False)  # DEMAND, PRODUCTION, PURCHASING, INVENTORY
    description = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON string for flexible payload

    def __repr__(self):
        return f"<EventLog(id={self.id}, day={self.day}, type={self.event_type}, category={self.category})>"
