"""Product catalog API endpoints for retailers."""
from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.config_service import ConfigService

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


class CatalogItemResponse(BaseModel):
    sku: str
    name: str
    unit_price: float


@router.get("", response_model=List[CatalogItemResponse])
def get_catalog(db: Session = Depends(get_db)):
    """List all finished product models with wholesale prices."""
    svc = ConfigService(db)
    return [{"sku": m.id, "name": m.name, "unit_price": float(m.wholesale_price)} for m in svc.get_models()]
