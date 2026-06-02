"""Unit tests for RetailerService pricing markup rule."""
import pytest
from unittest.mock import patch
from app.services.retailer_service import RetailerService
from app.models.product import ProductCatalogItem


def test_retailer_markup_rule(db_session, sample_inventory):
    """Test that the retailer enforces the 15% markup rule."""
    service = RetailerService(db=db_session)

    # Mock catalog: Classic at wholesale €195 → minimum retail €224.25
    mock_catalog = [
        ProductCatalogItem(sku="P3D-Classic", name="Classic", retail_price=295.0, wholesale_price=195.0)
    ]

    with patch.object(RetailerService, "get_catalog", return_value=mock_catalog):
        # Price below 15% markup (€200 < €224.25) → raises
        with pytest.raises(ValueError, match="below the minimum 15% markup"):
            service.set_retail_price("P3D-Classic", 200.0)

        # Valid price (€250 > €224.25)
        item = service.set_retail_price("P3D-Classic", 250.0)
        assert item.retail_price == 250.0
