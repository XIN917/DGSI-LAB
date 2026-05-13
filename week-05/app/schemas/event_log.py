"""Event Log schema definitions."""

from pydantic import BaseModel, Field
from typing import Optional


class EventLogResponse(BaseModel):
    id: str
    day: int
    timestamp: float
    event_type: str
    category: str
    description: str
    details: Optional[str] = None

    class Config:
        from_attributes = True


class EventLogCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    day: int = Field(..., ge=1)
    timestamp: float = Field(..., ge=0)
    event_type: str = Field(..., min_length=1, max_length=50)
    category: str = Field(..., min_length=1, max_length=20)
    description: str = Field(..., min_length=1)
    details: Optional[str] = None
