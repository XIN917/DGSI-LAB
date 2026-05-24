from pydantic import BaseModel


class EventLogEntry(BaseModel):
    sim_day: int
    event_type: str
    entity_type: str
    entity_id: int | None = None
    details: str


class SimState(BaseModel):
    current_day: int = 0
    manufacturer_url: str
    minimum_markup_pct: float
    recommended_markup_pct: float
