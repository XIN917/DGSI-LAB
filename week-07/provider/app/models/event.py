from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sim_day = Column(Integer, nullable=False)
    event_type = Column(String(100), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(Integer)
    detail = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
