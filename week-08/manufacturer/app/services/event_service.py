"""Event log service."""
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.event import EventLog


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def log(self, event_type: str, details: str, event_date=None) -> EventLog:
        event = EventLog(
            event_type=event_type,
            event_date=event_date or datetime.utcnow(),
            details=details,
        )
        self.db.add(event)
        self.db.commit()
        return event

    def list_events(
        self,
        event_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[int, List[EventLog]]:
        query = self.db.query(EventLog)
        if event_type:
            query = query.filter(EventLog.event_type == event_type)
        if date_from:
            query = query.filter(EventLog.event_date >= datetime.fromisoformat(date_from))
        if date_to:
            query = query.filter(EventLog.event_date <= datetime.fromisoformat(date_to + "T23:59:59"))
        total = query.count()
        events = (
            query.order_by(EventLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, events

    def export_events(self, event_type: Optional[str] = None) -> List[EventLog]:
        query = self.db.query(EventLog)
        if event_type:
            query = query.filter(EventLog.event_type == event_type)
        return query.order_by(EventLog.created_at.asc()).limit(10000).all()

    def get_event(self, event_id: int) -> Optional[EventLog]:
        return self.db.query(EventLog).filter(EventLog.id == event_id).first()
