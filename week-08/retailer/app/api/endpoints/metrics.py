from datetime import UTC, datetime
from fastapi import APIRouter
from sqlalchemy import text, select

from app.core import database as _db_module
from app.models.database import CustomerOrderDB, InventoryItemDB, SimStateDB

router = APIRouter()


async def _current_day() -> int:
    async with _db_module.AsyncSessionLocal() as session:
        result = await session.execute(select(SimStateDB.value).where(SimStateDB.key == "current_day"))
        row = result.first()
        return int(row.value) if row else 0


async def _ensure_table(session) -> None:
    await session.execute(
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


async def _insert(session, day: int, metric: str, entity: str, value: float) -> None:
    await session.execute(
        text(
            "INSERT INTO metrics_snapshots (sim_day, metric, entity, value, created_at) "
            "VALUES (:day, :metric, :entity, :value, :created_at)"
        ),
        {
            "day": day,
            "metric": metric,
            "entity": entity,
            "value": value,
            "created_at": datetime.now(UTC).isoformat(),
        },
    )


@router.post("/snapshot")
async def snapshot_metrics():
    day = await _current_day()
    async with _db_module.AsyncSessionLocal() as session:
        await _ensure_table(session)
        await session.execute(text("DELETE FROM metrics_snapshots WHERE sim_day = :day"), {"day": day})

        inventory = await session.execute(select(InventoryItemDB))
        for item in inventory.scalars():
            await _insert(session, day, "retailer_stock", item.sku, float(item.quantity_on_hand))
            await _insert(session, day, "retailer_price", item.sku, float(item.retail_price))

        statuses = ["fulfilled", "backordered", "pending", "cancelled"]
        total = await session.execute(select(CustomerOrderDB))
        orders = list(total.scalars())
        await _insert(session, day, "retailer_orders", "placed", float(len(orders)))
        for status in statuses:
            await _insert(
                session,
                day,
                "retailer_orders",
                status,
                float(len([order for order in orders if str(order.status) == status])),
            )

        await session.commit()
    return {"sim_day": day, "snapshotted": True}


@router.get("")
async def get_metrics():
    async with _db_module.AsyncSessionLocal() as session:
        await _ensure_table(session)
        rows = await session.execute(
            text(
                "SELECT sim_day, metric, entity, value, created_at "
                "FROM metrics_snapshots ORDER BY sim_day, metric, entity"
            )
        )
        return [dict(row) for row in rows.mappings()]
