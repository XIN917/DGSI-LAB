"""Unit tests for InventoryService."""
import pytest
from decimal import Decimal
from app.services.inventory_service import InventoryService


def test_get_all(db_session, sample_inventory):
    svc = InventoryService(db_session)
    items = svc.get_all()
    assert len(items) >= 7


def test_get_by_product(db_session, sample_inventory):
    svc = InventoryService(db_session)
    item = svc.get_by_product("frame_kit")
    assert item is not None
    assert float(item.quantity) == 100.0


def test_get_by_product_missing(db_session):
    svc = InventoryService(db_session)
    assert svc.get_by_product("nonexistent_part") is None


def test_get_available(db_session, sample_inventory):
    svc = InventoryService(db_session)
    available = svc.get_available("frame_kit")
    assert available == Decimal("100")


def test_reserve_success(db_session, sample_inventory):
    svc = InventoryService(db_session)
    success = svc.reserve("frame_kit", Decimal("30"))
    assert success is True
    item = svc.get_by_product("frame_kit")
    assert float(item.reserved_quantity) == 30.0
    assert svc.get_available("frame_kit") == Decimal("70")


def test_reserve_insufficient(db_session, sample_inventory):
    svc = InventoryService(db_session)
    success = svc.reserve("frame_kit", Decimal("200"))  # only 100 available
    assert success is False


def test_release_reservation(db_session, sample_inventory):
    svc = InventoryService(db_session)
    svc.reserve("frame_kit", Decimal("30"))
    success = svc.release_reservation("frame_kit", Decimal("30"))
    assert success is True
    item = svc.get_by_product("frame_kit")
    assert float(item.reserved_quantity) == 0.0


def test_consume(db_session, sample_inventory):
    svc = InventoryService(db_session)
    svc.reserve("frame_kit", Decimal("10"))
    success = svc.consume("frame_kit", Decimal("10"))
    assert success is True
    item = svc.get_by_product("frame_kit")
    assert float(item.quantity) == 90.0


def test_adjust_existing(db_session, sample_inventory):
    svc = InventoryService(db_session)
    item = svc.adjust("frame_kit", Decimal("999"))
    assert float(item.quantity) == 999.0


def test_adjust_new_product(db_session):
    svc = InventoryService(db_session)
    item = svc.adjust("new_exotic_part", Decimal("42"))
    assert item.product_name == "new_exotic_part"
    assert float(item.quantity) == 42.0


def test_warehouse_usage(db_session, sample_inventory):
    svc = InventoryService(db_session)
    usage = svc.get_warehouse_usage(1000)
    assert usage["capacity"] == 1000
    assert usage["used"] > 0
    assert 0 <= usage["percentage"] <= 200  # can exceed 100% if overstocked
