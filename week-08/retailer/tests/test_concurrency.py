"""Concurrency tests for the retailer service.

The intent is to surface race conditions that unit tests with a single
caller cannot. We exercise the atomic `reserve_inventory` and the
`create_customer_order` path under `asyncio.gather` with N simultaneous
in-flight calls against the same SKU and assert that the system never
oversells.

Background: the historic implementation did `get_inventory + reserve` in
two separate sessions. Two concurrent calls both passed the `>=` check
before either committed, oversold, and one customer ended up "fulfilled"
without stock. The fix made `reserve_inventory` a single
conditional UPDATE; this test would have caught the regression.
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.models.database import Base, InventoryItemDB, CustomerOrderDB, SimStateDB, OrderStatus
from app.services.retailer_service import RetailerService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    """Per-test async engine + factory bound to a temp sqlite file."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'race.db'}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        s.add(SimStateDB(key="current_day", value="0"))
        await s.commit()
    try:
        yield factory
    finally:
        await engine.dispose()


async def _seed_inventory(factory, sku: str, qty: int, price: float = 1500.0):
    async with factory() as s:
        s.add(InventoryItemDB(sku=sku, quantity_on_hand=qty, retail_price=price))
        await s.commit()


@pytest.mark.asyncio
async def test_reserve_inventory_never_oversells_under_concurrency(session_factory):
    """50 concurrent reservation attempts of 1 unit against a 10-unit
    stock: exactly 10 must succeed, 40 must return False, and final
    `quantity_on_hand` must be 0 (never negative)."""
    sku = "P3D-Classic"
    initial = 10
    await _seed_inventory(session_factory, sku, initial)
    service = RetailerService(session_local=session_factory)

    results = await asyncio.gather(
        *[service.reserve_inventory(sku, 1) for _ in range(50)]
    )

    successes = sum(1 for r in results if r is True)
    assert successes == initial, f"expected exactly {initial} successes, got {successes}"

    async with session_factory() as s:
        row = (await s.execute(select(InventoryItemDB).where(InventoryItemDB.sku == sku))).scalars().first()
        assert row.quantity_on_hand == 0, f"oversold: quantity_on_hand={row.quantity_on_hand}"
        assert row.quantity_reserved == initial


@pytest.mark.asyncio
async def test_create_customer_order_concurrent_does_not_oversell(session_factory):
    """20 concurrent customer orders for 1 unit each against 5-unit stock:
    5 must end as `fulfilled`, the remaining 15 as `backordered`. No
    invariant must allow the sum of fulfilled units to exceed initial
    on-hand stock.
    """
    sku = "P3D-Classic"
    initial = 5
    await _seed_inventory(session_factory, sku, initial)
    service = RetailerService(session_local=session_factory)

    await asyncio.gather(
        *[service.create_customer_order(sku, 1, customer_name=f"c-{i}") for i in range(20)]
    )

    async with session_factory() as s:
        orders = list((await s.execute(select(CustomerOrderDB))).scalars())
        inv = (await s.execute(select(InventoryItemDB).where(InventoryItemDB.sku == sku))).scalars().first()

    fulfilled = [o for o in orders if str(o.status) == "fulfilled"]
    backordered = [o for o in orders if str(o.status) == "backordered"]

    assert len(orders) == 20
    assert sum(o.quantity for o in fulfilled) <= initial, "oversold"
    assert len(fulfilled) == initial
    assert len(backordered) == 20 - initial
    assert inv.quantity_on_hand == 0


@pytest.mark.asyncio
async def test_reserve_inventory_rejects_when_below_threshold(session_factory):
    """Single call asking for more than is available must return False
    and not mutate state."""
    sku = "P3D-Pro"
    await _seed_inventory(session_factory, sku, 3)
    service = RetailerService(session_local=session_factory)

    ok = await service.reserve_inventory(sku, 5)
    assert ok is False

    async with session_factory() as s:
        row = (await s.execute(select(InventoryItemDB).where(InventoryItemDB.sku == sku))).scalars().first()
        assert row.quantity_on_hand == 3
        assert row.quantity_reserved == 0
