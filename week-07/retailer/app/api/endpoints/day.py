from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.retailer_service import RetailerService
from app.core.database import get_db

router = APIRouter()


@router.get("/current")
def get_current_day(db: Session = Depends(get_db)):
    """Get the current simulation day."""
    service = RetailerService(db)
    return {"current_day": service.get_current_day()}


@router.post("/advance")
def advance_day(db: Session = Depends(get_db)):
    """Advance the simulation to the next day."""
    service = RetailerService(db)
    return service.advance_day()
