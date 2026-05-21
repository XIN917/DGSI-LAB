from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.simulation import SimState

router = APIRouter()


class ScenarioEffects(BaseModel):
    lead_time_modifier: float = Field(default=1.0, ge=0)
    supply_modifier: float = Field(default=1.0, ge=0)


def _set_state(db: Session, key: str, value: str) -> None:
    row = db.query(SimState).filter(SimState.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SimState(key=key, value=value))


@router.post("/effects")
def set_effects(effects: ScenarioEffects, db: Session = Depends(get_db)):
    _set_state(db, "lead_time_modifier", str(effects.lead_time_modifier))
    _set_state(db, "supply_modifier", str(effects.supply_modifier))
    db.commit()
    return effects.model_dump()


@router.get("/effects")
def get_effects(db: Session = Depends(get_db)):
    values = {
        row.key: row.value
        for row in db.query(SimState)
        .filter(SimState.key.in_(["lead_time_modifier", "supply_modifier"]))
        .all()
    }
    return {
        "lead_time_modifier": float(values.get("lead_time_modifier", 1.0)),
        "supply_modifier": float(values.get("supply_modifier", 1.0)),
    }
