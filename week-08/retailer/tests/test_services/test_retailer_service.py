"""Tests for RetailerService business logic."""
import pytest

from app.services.retailer_service import RetailerService


class TestRetailerService:
    """Test RetailerService methods."""

    def test_get_current_day(self, db_session):
        service = RetailerService(db=db_session)
        assert service.get_current_day() == 0

    def test_set_current_day(self, db_session):
        service = RetailerService(db=db_session)
        service.set_current_day(5)
        assert service.get_current_day() == 5

    def test_get_catalog(self, db_session):
        service = RetailerService(db=db_session)
        catalog = service.get_catalog()
        assert len(catalog) == 2
        skus = {i.sku for i in catalog}
        assert "P3D-Classic" in skus and "P3D-Pro" in skus

    def test_create_customer_order_fulfilled(self, db_session, sample_inventory):
        service = RetailerService(db=db_session)
        order = service.create_customer_order("P3D-Classic", 2)
        assert order.sku == "P3D-Classic"
        assert order.quantity == 2
        assert order.status == "fulfilled"
        assert order.retail_price == 1500.0

    def test_create_customer_order_backordered(self, db_session, sample_inventory):
        service = RetailerService(db=db_session)
        order = service.create_customer_order("P3D-Pro", 10)  # Only 5 in stock
        assert order.sku == "P3D-Pro"
        assert order.quantity == 10
        assert order.status == "backordered"

    def test_advance_day(self, db_session):
        service = RetailerService(db=db_session)
        result = service.advance_day()
        assert "Advanced to day 1" in result["message"]
        assert service.get_current_day() == 1
