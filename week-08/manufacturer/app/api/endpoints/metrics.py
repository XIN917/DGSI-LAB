"""Daily metrics snapshots for Week 8 analysis."""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.inventory import Inventory
from app.models.order import ManufacturingOrder
from app.models.product import ProductModel
from app.models.simulation import SimulationState

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def _current_day(db: Session) -> int:
    state = db.query(SimulationState).first()
    return int(state.current_day) if state else 0


def _ensure_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS metrics_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sim_day INTEGER NOT NULL,
                metric TEXT NOT NULL,
                entity TEXT NOT NULL,
                value REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
    )


def _insert(db: Session, day: int, metric: str, entity: str, value: float) -> None:
    db.execute(
        text(
            "INSERT INTO metrics_snapshots (sim_day, metric, entity, value, created_at) "
            "VALUES (:day, :metric, :entity, :value, :created_at)"
        ),
        {
            "day": day,
            "metric": metric,
            "entity": entity,
            "value": value,
            "created_at": datetime.utcnow().isoformat(),
        },
    )


@router.post("/snapshot")
def snapshot_metrics(db: Session = Depends(get_db)):
    _ensure_table(db)
    day = _current_day(db)
    db.execute(text("DELETE FROM metrics_snapshots WHERE sim_day = :day"), {"day": day})

    for item in db.query(Inventory).all():
        metric = "manufacturer_raw_stock" if item.unit_type == "raw" else "manufacturer_finished_stock"
        _insert(db, day, metric, item.product_name, float(item.quantity))

    statuses = db.query(ManufacturingOrder.status).distinct().all()
    for (status,) in statuses:
        count = db.query(ManufacturingOrder).filter(ManufacturingOrder.status == status).count()
        _insert(db, day, "manufacturer_sales_orders", status, float(count))

    for model in db.query(ProductModel).all():
        _insert(db, day, "manufacturer_wholesale_price", model.id, float(model.wholesale_price))

    state = db.query(SimulationState).first()
    capacity = float(state.capacity_per_day if state else 0)
    released = db.query(ManufacturingOrder).filter(ManufacturingOrder.status == "released").count()
    utilization = min(1.0, released / capacity) if capacity else 0.0
    _insert(db, day, "manufacturer_production_utilization", "all", utilization)

    db.commit()
    return {"sim_day": day, "snapshotted": True}


@router.get("")
def get_metrics(db: Session = Depends(get_db)):
    _ensure_table(db)
    rows = db.execute(
        text(
            "SELECT sim_day, metric, entity, value, created_at "
            "FROM metrics_snapshots ORDER BY sim_day, metric, entity"
        )
    ).mappings()
    return [dict(row) for row in rows]
