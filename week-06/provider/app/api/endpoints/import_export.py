"""Import/Export API endpoints for full Provider state."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.utils.json_export import export_full_state, import_full_state

router = APIRouter(prefix="/api", tags=["import-export"])

@router.get("/export/full-state")
def export_state(db: Session = Depends(get_db)):
    """Export complete provider state as JSON (products, orders, events, sim_state)."""
    return export_full_state(db)

@router.post("/import/full-state")
def import_state(data: dict, db: Session = Depends(get_db)):
    """
    Import a complete provider state.
    WARNING: Replaces all simulation data.
    """
    try:
        result = import_full_state(db, data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    return result
