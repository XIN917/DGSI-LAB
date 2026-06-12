"""Simulation control API endpoints."""
from typing import Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.event import EventLog
from app.services.simulation_engine import SimulationEngine
from datetime import datetime

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


class DemandParams(BaseModel):
    params: Dict[str, Dict[str, float]]


class AdvanceDayResponse(BaseModel):
    previous_day: int
    new_day: int
    current_date: str
    events_generated: list


class SimulationStatus(BaseModel):
    current_day: int
    current_date: str
    sim_start_date: str
    pending_orders_count: int
    capacity_per_day: int


@router.get("/status", response_model=SimulationStatus)
def get_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get current simulation state (day, date, pending orders, capacity)."""
    engine = SimulationEngine(db)
    return engine.get_status()


@router.post("/advance", response_model=AdvanceDayResponse)
def advance_day(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Advance the simulation by one day and return all generated events."""
    engine = SimulationEngine(db)
    result = engine.advance_day()

    event = EventLog(
        event_type="day_advanced",
        event_date=datetime.utcnow(),
        details=str({
            "from_day": result["previous_day"],
            "to_day": result["new_day"],
            "user": current_user.username,
        }),
    )
    db.add(event)
    db.commit()

    return result


@router.get("/demand-params")
def get_demand_params(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get current demand parameters per product model."""
    engine = SimulationEngine(db)
    return engine.get_demand_params()


@router.post("/demand-params")
def update_demand_params(
    body: DemandParams,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update demand parameters (mean and variance per model)."""
    engine = SimulationEngine(db)
    engine.update_demand_params(body.params)
    return {"message": "Demand parameters updated", "params": body.params}
