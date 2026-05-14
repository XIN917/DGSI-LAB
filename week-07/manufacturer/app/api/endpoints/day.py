"""Simulation day API endpoints (aliases for retailer compatibility)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.simulation_engine import SimulationEngine

router = APIRouter(prefix="/api/day", tags=["simulation"])


@router.get("/current")
def get_current_day(db: Session = Depends(get_db)):
    """Get current simulation day."""
    engine = SimulationEngine(db)
    return {"current_day": engine.current_day}


@router.post("/advance")
def advance_day(db: Session = Depends(get_db)):
    """Advance the simulation by one day."""
    engine = SimulationEngine(db)
    result = engine.advance_day()
    return result
