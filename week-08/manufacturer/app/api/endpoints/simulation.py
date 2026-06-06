"""Simulation control API endpoints."""
from typing import Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.external_supplier_service import ExternalSupplierService
from app.services.simulation_engine import SimulationEngine

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
def get_status(db: Session = Depends(get_db)):
    """Get current simulation state (day, date, pending orders, capacity)."""
    return SimulationEngine(db).get_status()


@router.post("/advance", response_model=AdvanceDayResponse)
def advance_day(db: Session = Depends(get_db)):
    """Advance the simulation by one day and return all generated events."""
    ExternalSupplierService(db).poll_orders()
    return SimulationEngine(db).advance_day()


@router.get("/demand-params")
def get_demand_params(db: Session = Depends(get_db)):
    """Get current demand parameters per product model."""
    return SimulationEngine(db).get_demand_params()


@router.post("/demand-params")
def update_demand_params(body: DemandParams, db: Session = Depends(get_db)):
    """Update demand parameters (mean and variance per model)."""
    SimulationEngine(db).update_demand_params(body.params)
    return {"message": "Demand parameters updated", "params": body.params}
