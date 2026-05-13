"""Event Log API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import EventLog
from app.schemas.event_log import EventLogResponse

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("", response_model=List[EventLogResponse])
def list_events(
    day: Optional[int] = Query(None, description="Filter by day"),
    category: Optional[str] = Query(None, description="Filter by category"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    db: Session = Depends(get_db),
):
    """List events with optional filters."""
    query = db.query(EventLog)

    if day:
        query = query.filter(EventLog.day == day)
    if category:
        query = query.filter(EventLog.category == category)
    if event_type:
        query = query.filter(EventLog.event_type == event_type)

    query = query.order_by(EventLog.day.desc(), EventLog.timestamp.desc())
    return query.limit(limit).all()


@router.get("/timeline")
def get_event_timeline(
    start_day: Optional[int] = Query(None, description="Start day"),
    end_day: Optional[int] = Query(None, description="End day"),
    db: Session = Depends(get_db),
):
    """Get events grouped by day for charting."""
    query = db.query(EventLog)

    if start_day:
        query = query.filter(EventLog.day >= start_day)
    if end_day:
        query = query.filter(EventLog.day <= end_day)

    events = query.order_by(EventLog.day, EventLog.timestamp).all()

    # Group by day
    timeline = {}
    for event in events:
        if event.day not in timeline:
            timeline[event.day] = []
        timeline[event.day].append({
            "type": event.event_type,
            "category": event.category,
            "description": event.description,
        })

    return {"timeline": timeline}
