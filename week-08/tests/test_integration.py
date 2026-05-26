import httpx
import pytest
import sqlite3
import os
from pathlib import Path

# Paths to databases
ROOT = Path(__file__).parent.parent
PROVIDER_DB = ROOT / "provider/data/provider.db"
MANUFACTURER_DB = ROOT / "manufacturer/data/manufacturer.db"
RETAILER_DB = ROOT / "retailer/data/retailer.db"

def get_metrics_count(db_path, day):
    if not os.path.exists(db_path):
        return 0
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM metrics WHERE sim_day = ?", (day,))
        count = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        count = -1 # Table doesn't exist
    finally:
        conn.close()
    return count

@pytest.mark.asyncio
async def test_services_health():
    async with httpx.AsyncClient() as client:
        for port in [8001, 8002, 8003]:
            try:
                resp = await client.get(f"http://127.0.0.1:{port}/api/day/current")
                assert resp.status_code == 200
            except httpx.ConnectError:
                pytest.fail(f"Service on port {port} is not running. Run ./scripts/start_all.sh first.")

@pytest.mark.asyncio
async def test_full_day_advance_logic():
    """
    Simulates what turn_engine does:
    1. Check Day 0
    2. Advance to Day 1 with a lead_time_modifier
    3. Verify metrics were snapshotted
    """
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # 1. Verify we are at Day 0 (assuming fresh reset)
        resp = await client.get("http://127.0.0.1:8001/api/day/current")
        data = resp.json()
        current_day = data.get("current_day")
        if current_day is None:
             current_day = data # Fallback if structure is different
            
        next_day = current_day + 1
        
        # 2. Advance all services
        # Provider with lead_time_modifier
        resp = await client.post("http://127.0.0.1:8001/api/day/advance", json={"lead_time_modifier": 2.0})
        assert resp.status_code == 200
        
        # Manufacturer
        resp = await client.post("http://127.0.0.1:8002/api/day/advance")
        assert resp.status_code == 200
        
        # Retailer
        resp = await client.post("http://127.0.0.1:8003/api/day/advance")
        assert resp.status_code == 200
        
        # 3. Verify Day incremented
        resp = await client.get("http://127.0.0.1:8001/api/day/current")
        assert resp.json()["current_day"] == next_day
        
        # 4. Verify metrics snapshots in DB
        assert get_metrics_count(PROVIDER_DB, next_day) > 0, "Provider metrics not found"
        assert get_metrics_count(MANUFACTURER_DB, next_day) > 0, "Manufacturer metrics not found"
        assert get_metrics_count(RETAILER_DB, next_day) > 0, "Retailer metrics not found"

@pytest.mark.asyncio
async def test_provider_lead_time_modifier():
    """Verify that lead_time_modifier affects new orders."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Set modifier to 3.0
        await client.post("http://127.0.0.1:8001/api/day/advance", json={"lead_time_modifier": 3.0})
        
        # Get current day
        day_resp = await client.get("http://127.0.0.1:8001/api/day/current")
        current_day = day_resp.json()["current_day"]
        
        # Get catalog to find a product
        cat_resp = await client.get("http://127.0.0.1:8001/api/catalog/")
        products = cat_resp.json()
        product = products[0]
        base_lead_time = product["lead_time_days"]
        
        # Place order
        order_resp = await client.post("http://127.0.0.1:8001/api/orders/", json={
            "buyer": "TestBuyer",
            "product_id": product["id"],
            "quantity": 10
        })
        assert order_resp.status_code == 200
        order = order_resp.json()
        
        # expected_delivery_day = current_day + int(base_lead_time * 3.0)
        expected = current_day + int(base_lead_time * 3.0)
        assert order["expected_delivery_day"] == expected
