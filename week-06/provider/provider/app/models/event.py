"""Event model for Provider app - audit trail."""
from sqlalchemy import Column, Integer, String, Text, DateTime
from provider.app.db import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sim_day = Column(Integer, nullable=False)
    event_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "sim_day": self.sim_day,
            "event_type": self.event_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "detail": self.detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }