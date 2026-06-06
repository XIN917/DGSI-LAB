"""Event log API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.event_service import EventService

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
    event_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List events with optional filtering and pagination."""
    svc = EventService(db)
    total, events = svc.list_events(event_type, date_from, date_to, page, page_size)
    return {"total": total, "page": page, "page_size": page_size, "items": [_serialize(e) for e in events]}


@router.get("/export")
def export_events(
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Export event log as JSON (up to 10,000 records)."""
    svc = EventService(db)
    events = svc.export_events(event_type)
    return {"events": [_serialize(e) for e in events], "total": len(events)}


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get details of a specific event."""
    svc = EventService(db)
    event = svc.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event #{event_id} not found")
    return _serialize(event)


def _serialize(event) -> dict:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "details": event.details,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
