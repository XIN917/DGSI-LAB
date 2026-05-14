"""Unit tests for ProviderService."""
import pytest
from decimal import Decimal
from app.services.provider_service import ProviderService
from app.models.product import Product, PricingTier

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
