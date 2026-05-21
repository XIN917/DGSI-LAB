from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.order import Order
from app.models.product import PricingTier, Stock
from app.models.simulation import SimState

router = APIRouter()


def _current_day(db: Session) -> int:
    row = db.query(SimState).filter(SimState.key == "current_day").first()
    return int(row.value) if row else 0


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

    for stock in db.query(Stock).all():
        _insert(db, day, "provider_stock", str(stock.product_id), float(stock.quantity))

    for tier in db.query(PricingTier).all():
        entity = f"{tier.product_id}:min_{tier.min_quantity}"
        _insert(db, day, "provider_price", entity, float(tier.unit_price))

    statuses = db.query(Order.status).distinct().all()
    for (status,) in statuses:
        count = db.query(Order).filter(Order.status == status).count()
        _insert(db, day, "provider_orders", status, float(count))

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
