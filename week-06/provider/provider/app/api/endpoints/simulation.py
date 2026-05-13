"""Simulation endpoints for Provider app."""
from fastapi import APIRouter

from provider.app.services.order_service import advance_day, get_current_day

router = APIRouter(prefix="/api", tags=["simulation"])


@router.post("/day/advance")
def day_advance():
    """Advance simulation by one day."""
    result = advance_day()
    return result


@router.get("/day/current")
def day_current():
    """Get current simulation day."""
    day = get_current_day()
    return {"current_day": day}