from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.provider_service import ProviderService
from app.api.schemas import DayAdvanceRequest, DayAdvanceResponse

router = APIRouter()

@router.post("/advance", response_model=DayAdvanceResponse)
def advance_day(body: DayAdvanceRequest = DayAdvanceRequest(), db: Session = Depends(get_db)):
    service = ProviderService(db)
    previous_day = service.get_current_day()
    new_day = service.advance_day(lead_time_modifier=body.lead_time_modifier)
    return {"previous_day": previous_day, "new_day": new_day}

@router.get("/current")
def get_current_day(db: Session = Depends(get_db)):
    service = ProviderService(db)
    return {"current_day": service.get_current_day()}
