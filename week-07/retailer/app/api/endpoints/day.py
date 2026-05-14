from fastapi import APIRouter

from app.services.retailer_service import RetailerService

router = APIRouter()
service = RetailerService()


@router.get("/current")
async def get_current_day():
    """Get current simulated day."""
    current_day = await service.get_current_day()
    return {"current_day": current_day}


@router.post("/advance")
async def advance_day():
    """Advance the simulation by one day."""
    return await service.advance_day()
