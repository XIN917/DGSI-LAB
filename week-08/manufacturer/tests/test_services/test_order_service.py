"""Unit tests for OrderService."""
import pytest
from datetime import datetime
from decimal import Decimal
from app.services.order_service import OrderService


def test_create_order(db_session, sample_model):
    svc = OrderService(db_session)
    order = svc.create("TEST-Model", Decimal("10"), datetime.utcnow())
    assert order.id is not None
    assert order.product_model == "TEST-Model"
    assert order.status == "pending"
    assert float(order.quantity_needed) == 10.0


def test_get_all_orders(db_session, sample_model):
    svc = OrderService(db_session)
    svc.create("TEST-Model", Decimal("5"), datetime.utcnow())
    svc.create("TEST-Model", Decimal("3"), datetime.utcnow())
    orders = svc.get_all()
    assert len(orders) == 2


def test_get_pending(db_session, sample_model, sample_inventory):
    svc = OrderService(db_session)
    order = svc.create("TEST-Model", Decimal("5"), datetime.utcnow())
    pending = svc.get_pending()
    assert len(pending) >= 1
    assert any(o.id == order.id for o in pending)


def test_get_by_id(db_session, sample_model):
    svc = OrderService(db_session)
    order = svc.create("TEST-Model", Decimal("5"), datetime.utcnow())
    found = svc.get_by_id(order.id)
    assert found is not None
    assert found.id == order.id


def test_get_by_id_missing(db_session):
    svc = OrderService(db_session)
    assert svc.get_by_id(99999) is None


def test_calculate_bom_requirements(db_session, sample_model, sample_inventory):
    svc = OrderService(db_session)
    order = svc.create("TEST-Model", Decimal("5"), datetime.utcnow())
    reqs = svc.calculate_bom_requirements(order)
    # 5 units × 1 frame_kit = 5 required, 100 available
    assert "frame_kit" in reqs
    assert reqs["frame_kit"]["required"] == 5.0
    assert reqs["frame_kit"]["available"] == 100.0
    assert reqs["frame_kit"]["sufficient"] is True
    # 5 units × 2 stepper_motors = 10 required
    assert "stepper_motor" in reqs
    assert reqs["stepper_motor"]["required"] == 10.0


def test_release_success(db_session, sample_model, sample_inventory):
    svc = OrderService(db_session)
    order = svc.create("TEST-Model", Decimal("5"), datetime.utcnow())
    success, error = svc.release(order.id)
    assert success is True
    assert error is None
    updated = svc.get_by_id(order.id)
    assert updated.status == "released"


def test_release_already_released(db_session, sample_model, sample_inventory):
    svc = OrderService(db_session)
    order = svc.create("TEST-Model", Decimal("5"), datetime.utcnow())
    svc.release(order.id)
    success, error = svc.release(order.id)
    assert success is False
    assert "released" in error


def test_cancel_pending_order(db_session, sample_model):
    svc = OrderService(db_session)
    order = svc.create("TEST-Model", Decimal("5"), datetime.utcnow())
    success = svc.cancel(order.id)
    assert success is True
    updated = svc.get_by_id(order.id)
    assert updated.status == "cancelled"


def test_cancel_released_releases_reservation(db_session, sample_model, sample_inventory):
    from app.services.inventory_service import InventoryService
    svc = OrderService(db_session)
    inv_svc = InventoryService(db_session)

    order = svc.create("TEST-Model", Decimal("5"), datetime.utcnow())
    svc.release(order.id)

    frame_before = inv_svc.get_by_product("frame_kit")
    assert float(frame_before.reserved_quantity) == 5.0

    svc.cancel(order.id)
    frame_after = inv_svc.get_by_product("frame_kit")
    assert float(frame_after.reserved_quantity) == 0.0
