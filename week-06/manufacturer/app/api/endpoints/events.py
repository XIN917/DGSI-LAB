"""Event log API endpoints."""
import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.event import EventLog

router = APIRouter(prefix="/api/events", tags=["events"])


class EventResponse(BaseModel):
    id: int
    event_type: str
    event_date: str
    details: str
    created_at: Optional[str] = None


class PaginatedEventsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[EventResponse]


@router.get("", response_model=PaginatedEventsResponse)
def list_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    date_from: Optional[str] = Query(None, description="Filter events from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter events until date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List events with optional filtering and pagination."""
    query = db.query(EventLog)

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

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize(e) for e in events],
    }


@router.get("/export")
def export_events(
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Export event log as JSON (up to 10,000 records)."""
    query = db.query(EventLog)
    if event_type:
        query = query.filter(EventLog.event_type == event_type)
    events = query.order_by(EventLog.created_at.asc()).limit(10000).all()
    return {"events": [_serialize(e) for e in events], "total": len(events)}


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get details of a specific event."""
    event = db.query(EventLog).filter(EventLog.id == event_id).first()
    if not event:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Event #{event_id} not found")
    return _serialize(event)


def _serialize(event: EventLog) -> dict:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "details": event.details,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
