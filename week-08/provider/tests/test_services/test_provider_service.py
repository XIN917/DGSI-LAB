"""Unit tests for ProviderService."""
import pytest
from decimal import Decimal
from app.services.provider_service import ProviderService
from app.models.product import Product, PricingTier, Stock
from app.models.simulation import SimState

def test_provider_catalog(db_session):
    """Test retrieving the provider catalog."""
    # Setup
    p1 = Product(id=1, name="PCB", lead_time_days=3)
    p2 = Product(id=2, name="Motor", lead_time_days=5)
    db_session.add_all([p1, p2])
    db_session.commit()

    service = ProviderService(db_session)
    catalog = service.get_catalog()
    
    assert len(catalog) == 2
    assert any(p.name == "PCB" for p in catalog)

def test_provider_pricing_tiers(db_session):
    """Test setting and getting pricing tiers."""
    p1 = Product(id=1, name="PCB", lead_time_days=3)
    db_session.add(p1)
    db_session.commit()

    service = ProviderService(db_session)
    service.set_price(1, 10, Decimal("20.00"))
    service.set_price(1, 100, Decimal("15.00"))
    
    catalog = service.get_catalog()
    product = catalog[0]
    assert len(product.pricing_tiers) == 2
    assert any(t.min_quantity == 100 and t.unit_price == Decimal("15.00") for t in product.pricing_tiers)


def test_provider_rejects_non_positive_order_quantity(db_session):
    p1 = Product(id=1, name="PCB", lead_time_days=3)
    db_session.add(p1)
    db_session.commit()

    service = ProviderService(db_session)

    with pytest.raises(ValueError, match="Quantity must be positive"):
        service.place_order("Manufacturer", 1, 0)


def test_provider_supply_modifier_never_reduces_stock(db_session):
    p1 = Product(id=1, name="PCB", lead_time_days=3)
    stock = Stock(product_id=1, quantity=10)
    db_session.add_all([p1, stock, SimState(key="supply_modifier", value="0")])
    db_session.commit()

    service = ProviderService(db_session)
    service.restock(1, 5)

    assert db_session.query(Stock).filter(Stock.product_id == 1).first().quantity == 10


def test_provider_restock_rejects_unknown_product(db_session):
    service = ProviderService(db_session)

    with pytest.raises(ValueError, match="Product not found"):
        service.restock(999, 5)


def test_provider_lead_time_modifier_has_minimum_one_day(db_session):
    p1 = Product(id=1, name="PCB", lead_time_days=3)
    db_session.add_all([p1, SimState(key="lead_time_modifier", value="0")])
    db_session.commit()

    service = ProviderService(db_session)
    service.set_price(1, 1, Decimal("10.00"))
    order = service.place_order("Manufacturer", 1, 2)

    assert order.expected_delivery_day == 1
