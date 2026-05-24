"""Unit tests for RetailerService."""
import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal
from app.services.retailer_service import RetailerService
from app.models.product import ProductCatalogItem

@pytest.mark.asyncio
async def test_retailer_markup_rule(db_session):
    """Test that the retailer enforces the 15% markup rule."""
    service = RetailerService()
    
    # Mock manufacturer catalog: Classic printer at $1000
    mock_catalog = [
        ProductCatalogItem(sku="P3D-Classic", name="Classic", retail_price=1300.0, wholesale_price=1000.0)
    ]
    
    with patch.object(RetailerService, 'get_catalog', return_value=mock_catalog):
        # 1. Try a price below 15% markup ($1100 < $1150)
        with pytest.raises(ValueError, match="below the minimum 15% markup"):
            await service.set_retail_price("P3D-Classic", 1100.0)
            
        # 2. Try a valid price ($1200 > $1150)
        item = await service.set_retail_price("P3D-Classic", 1200.0)
        assert item.retail_price == 1200.0
