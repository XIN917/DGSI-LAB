"""Event Log model."""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class EventLog(Base):
    """Event log for tracking all simulation events (append-only)."""
    __tablename__ = "event_log"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # order_released, material_consumed, po_created, etc.
    event_date = Column(DateTime(timezone=True), nullable=False)
    details = Column(Text, nullable=False)  # JSON string with context-specific payload
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<EventLog(id={self.id}, type='{self.event_type}', date='{self.event_date}')>"
