from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.services.provider_service import ProviderService
from app.api.schemas import ProductSchema

router = APIRouter()

@router.get("/", response_model=List[ProductSchema])
def get_catalog(db: Session = Depends(get_db)):
    service = ProviderService(db)
    return service.get_catalog()
