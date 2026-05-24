from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.services.provider_service import ProviderService
from app.api.schemas import StockSchema

router = APIRouter()

@router.get("/", response_model=List[StockSchema])
def get_stock(db: Session = Depends(get_db)):
    service = ProviderService(db)
    return service.get_stock()
