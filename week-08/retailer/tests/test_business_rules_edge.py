"""Edge-case tests for retailer business rules.

These exercise the boundaries of the retailer's API contract and the
recent defensive-logging fixes. The goal is to pin behaviors that are
easy to regress silently because they live in error paths.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from unittest.mock import AsyncMock, patch

from app.models.database import (
    Base,
    InventoryItemDB,
    CustomerOrderDB,
    PurchaseOrderDB,
    EventLogDB,
    SimStateDB,
    OrderStatus,
)
from app.services.retailer_service import RetailerService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'edge.db'}", echo=False)
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


async def _seed(factory, **kwargs):
    """Insert one InventoryItemDB row."""
    async with factory() as s:
        s.add(InventoryItemDB(**kwargs))
        await s.commit()


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_customer_order_rejects_negative_quantity(session_factory):
    service = RetailerService(session_local=session_factory)
    with pytest.raises(ValueError, match="positive"):
        await service.create_customer_order("P3D-Classic", -3)


@pytest.mark.asyncio
async def test_create_customer_order_rejects_zero_quantity(session_factory):
    service = RetailerService(session_local=session_factory)
    with pytest.raises(ValueError, match="positive"):
        await service.create_customer_order("P3D-Classic", 0)


@pytest.mark.asyncio
async def test_create_customer_order_rejects_unknown_sku(session_factory):
    service = RetailerService(session_local=session_factory)
    with pytest.raises(ValueError, match="Unknown SKU"):
        await service.create_customer_order("P3D-Mythical", 1)


@pytest.mark.asyncio
async def test_create_purchase_order_rejects_non_positive_quantity(session_factory):
    service = RetailerService(session_local=session_factory)
    with pytest.raises(ValueError, match="positive"):
        await service.create_purchase_order("P3D-Classic", 0)


@pytest.mark.asyncio
async def test_set_retail_price_rejects_non_positive(session_factory):
    service = RetailerService(session_local=session_factory)
    with pytest.raises(ValueError, match="positive"):
        await service.set_retail_price("P3D-Classic", 0)


@pytest.mark.asyncio
async def test_set_retail_price_rejects_below_markup_floor(session_factory):
    """The 15% minimum markup rule. We patch get_catalog so the test
    doesn't depend on the real manufacturer service."""
    await _seed(session_factory, sku="P3D-Classic", quantity_on_hand=10, retail_price=1500.0)
    service = RetailerService(session_local=session_factory)

    fake_catalog = [type("X", (), {"sku": "P3D-Classic", "wholesale_price": 1200.0, "retail_price": 1500.0})()]
    with patch.object(service, "get_catalog", AsyncMock(return_value=fake_catalog)):
        with pytest.raises(ValueError, match="15%"):
            # 1200 * 1.15 = 1380. Anything below should be rejected.
            await service.set_retail_price("P3D-Classic", 1300)


# ---------------------------------------------------------------------------
# Inventory operations on missing rows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reserve_inventory_on_unknown_sku_returns_false(session_factory):
    """The atomic UPDATE matches zero rows; the function must not crash."""
    service = RetailerService(session_local=session_factory)
    ok = await service.reserve_inventory("P3D-Classic", 1)
    assert ok is False


@pytest.mark.asyncio
async def test_get_inventory_item_on_unknown_sku_returns_none(session_factory):
    service = RetailerService(session_local=session_factory)
    assert await service.get_inventory_item("P3D-Classic") is None


@pytest.mark.asyncio
async def test_receive_inventory_creates_row_when_sku_absent(session_factory):
    """When a manufacturer delivers a SKU we never had locally, the
    retailer must create an inventory row (not silently drop the stock)."""
    service = RetailerService(session_local=session_factory)

    await service.receive_inventory("P3D-Pro", quantity=5, cost=2000.0)

    async with session_factory() as s:
        row = (
            await s.execute(select(InventoryItemDB).where(InventoryItemDB.sku == "P3D-Pro"))
        ).scalars().first()
        assert row is not None
        assert row.quantity_on_hand == 5
        assert row.last_cost == 2000.0


# ---------------------------------------------------------------------------
# Backorder behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_backorders_is_noop_when_none_pending(session_factory):
    """No backorders, no inventory mutation, no crash."""
    await _seed(session_factory, sku="P3D-Classic", quantity_on_hand=10, retail_price=1500.0)
    service = RetailerService(session_local=session_factory)
    await service.process_backorders()  # must not raise


@pytest.mark.asyncio
async def test_process_backorders_fulfills_oldest_first(session_factory):
    """Two backorders for the same SKU with only enough stock for one:
    the oldest (by created_day, then id) must be fulfilled first."""
    sku = "P3D-Classic"
    await _seed(session_factory, sku=sku, quantity_on_hand=1, retail_price=1500.0)

    async with session_factory() as s:
        old = CustomerOrderDB(
            sku=sku, quantity=1, retail_price=1500.0, status=OrderStatus.backordered, created_day=1
        )
        new = CustomerOrderDB(
            sku=sku, quantity=1, retail_price=1500.0, status=OrderStatus.backordered, created_day=5
        )
        s.add_all([old, new])
        await s.commit()

    service = RetailerService(session_local=session_factory)
    await service.process_backorders()

    async with session_factory() as s:
        orders = list((await s.execute(select(CustomerOrderDB).order_by(CustomerOrderDB.created_day))).scalars())
        assert str(orders[0].status) == "fulfilled"
        assert str(orders[1].status) == "backordered"


@pytest.mark.asyncio
async def test_backorder_stays_backordered_when_partial_stock(session_factory):
    """If the customer wanted 5 but stock is only 3, the order must stay
    backordered (no partial fulfillment) and stock must remain at 3."""
    sku = "P3D-Classic"
    await _seed(session_factory, sku=sku, quantity_on_hand=3, retail_price=1500.0)

    async with session_factory() as s:
        s.add(
            CustomerOrderDB(
                sku=sku, quantity=5, retail_price=1500.0, status=OrderStatus.backordered, created_day=1
            )
        )
        await s.commit()

    service = RetailerService(session_local=session_factory)
    await service.process_backorders()

    async with session_factory() as s:
        order = (await s.execute(select(CustomerOrderDB))).scalars().first()
        inv = (await s.execute(select(InventoryItemDB).where(InventoryItemDB.sku == sku))).scalars().first()
        assert str(order.status) == "backordered"
        assert inv.quantity_on_hand == 3


# ---------------------------------------------------------------------------
# Resilience to upstream failures (the C3 + M3 fixes)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_purchase_order_deliveries_logs_when_manufacturer_down(session_factory):
    """The C3 fix: a failed sync must produce an event log row, not be
    silently swallowed."""
    async with session_factory() as s:
        s.add(
            PurchaseOrderDB(
                manufacturer_po_id=42,
                sku="P3D-Classic",
                quantity=10,
                wholesale_unit_price=1200.0,
                retail_unit_price=0.0,
                status="pending",
                placed_day=1,
            )
        )
        await s.commit()

    service = RetailerService(session_local=session_factory)
    with patch.object(
        service.manufacturer_client,
        "get_order",
        AsyncMock(side_effect=ConnectionError("manufacturer down")),
    ):
        await service.check_purchase_order_deliveries()  # must NOT raise

    async with session_factory() as s:
        events = list(
            (
                await s.execute(
                    select(EventLogDB).where(EventLogDB.event_type == "purchase_order_sync_failed")
                )
            ).scalars()
        )
        assert len(events) == 1
        assert "manufacturer down" in events[0].details


@pytest.mark.asyncio
async def test_get_catalog_logs_when_manufacturer_unreachable(session_factory):
    """The M3 fix: the hardcoded-fallback catalog path must log the
    upstream error so silent drift is detectable."""
    service = RetailerService(session_local=session_factory)
    with patch.object(
        service.manufacturer_client,
        "get_catalog",
        AsyncMock(side_effect=ConnectionError("network unreachable")),
    ):
        catalog = await service.get_catalog()

    # Fallback returns the two known SKUs.
    skus = {item.sku for item in catalog}
    assert skus == {"P3D-Classic", "P3D-Pro"}

    async with session_factory() as s:
        events = list(
            (
                await s.execute(
                    select(EventLogDB).where(EventLogDB.event_type == "catalog_fallback")
                )
            ).scalars()
        )
        assert len(events) == 1
        assert "network unreachable" in events[0].details


# ---------------------------------------------------------------------------
# Sim state lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_advance_day_increments_and_persists(session_factory):
    service = RetailerService(session_local=session_factory)

    assert await service.get_current_day() == 0
    await service.advance_day()
    assert await service.get_current_day() == 1
    await service.advance_day()
    assert await service.get_current_day() == 2


@pytest.mark.asyncio
async def test_get_current_day_returns_zero_when_state_missing(tmp_path):
    """Fresh DB with no SimStateDB row must report day 0, not crash."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'fresh.db'}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    service = RetailerService(session_local=factory)

    try:
        assert await service.get_current_day() == 0
    finally:
        await engine.dispose()
