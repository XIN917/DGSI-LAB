import asyncio
import sqlite3
import httpx
from pathlib import Path
from dashboard.collector import collect_tier
from dashboard.config import ServiceConfig


def _provider_handler(request: httpx.Request) -> httpx.Response:
    p = request.url.path
    if p == "/api/day/current":
        return httpx.Response(200, json={"current_day": 14})
    if p == "/api/stock/":
        return httpx.Response(200, json=[{"product_id": 1, "quantity": 40}, {"product_id": 2, "quantity": 88}])
    if p == "/api/catalog/":
        return httpx.Response(200, json=[
            {"id": 1, "name": "chip", "lead_time_days": 5, "pricing_tiers": [{"min_quantity": 1, "unit_price": 12.0}, {"min_quantity": 50, "unit_price": 10.0}]},
            {"id": 2, "name": "frame", "lead_time_days": 3, "pricing_tiers": [{"min_quantity": 1, "unit_price": 30.0}]}])
    if p == "/api/orders/":
        return httpx.Response(200, json=[
            {"id": 312, "buyer": "Factory", "product_id": 1, "quantity": 40, "status": "SHIPPED", "expected_delivery_day": 16},
            {"id": 300, "buyer": "Factory", "product_id": 1, "quantity": 10, "status": "DELIVERED", "expected_delivery_day": 12}])
    return httpx.Response(404)


def test_collect_provider_normalizes_and_joins_catalog():
    svc = ServiceConfig("ChipSupply", "http://prov", Path("x.db"))
    client = httpx.AsyncClient(transport=httpx.MockTransport(_provider_handler))
    tier = asyncio.run(collect_tier("provider", svc, client))
    asyncio.run(client.aclose())

    assert tier["online"] is True
    assert tier["current_day"] == 14
    chip = next(i for i in tier["items"] if i["name"] == "chip")
    assert chip["stock"] == 40 and chip["price"] == 12.0 and chip["lead"] == 5 and chip["capacity"] is None
    # only open orders count toward in_transit_out (SHIPPED yes, DELIVERED no)
    assert tier["in_transit_out"] == 40
    assert any(o["id"] == 312 and o["eta"] == 16 for o in tier["orders"])


_MFR_INVENTORY = {
    "items": [
        {"product_name": "P3D-Classic", "quantity": 12.0, "reserved_quantity": 0.0,
         "available": 12.0, "max_capacity": 250.0, "unit_type": "finished"},
        {"product_name": "P3D-Pro",     "quantity": 5.0,  "reserved_quantity": 0.0,
         "available": 5.0,  "max_capacity": 250.0, "unit_type": "finished"},
        {"product_name": "frame_kit",   "quantity": 20.0, "reserved_quantity": 0.0,
         "available": 20.0, "max_capacity": 250.0, "unit_type": "raw"},
        {"product_name": "pcb_control", "quantity": 200.0,"reserved_quantity": 0.0,
         "available": 200.0,"max_capacity": 250.0, "unit_type": "raw"},
    ],
    "total_units": 237.0, "capacity": 1000, "usage_pct": 23.7,
}

_MFR_ORDERS = [
    {"id": 10, "product_model": "P3D-Classic", "quantity_needed": 5.0, "quantity_produced": 0.0,
     "status": "pending", "delivery_day": None},
    {"id": 11, "product_model": "P3D-Pro", "quantity_needed": 3.0, "quantity_produced": 3.0,
     "status": "completed", "delivery_day": 7},
]


def _mfr_handler(request: httpx.Request) -> httpx.Response:
    p = request.url.path
    if p == "/api/day/current":
        return httpx.Response(200, json={"current_day": 7})
    if p == "/api/catalog":
        return httpx.Response(200, json=[
            {"sku": "P3D-Classic", "name": "P3D Classic", "unit_price": 1200.0},
            {"sku": "P3D-Pro", "name": "P3D Pro", "unit_price": 246.0}])
    if p == "/api/inventory":
        return httpx.Response(200, json=_MFR_INVENTORY)
    if p == "/api/orders":
        return httpx.Response(200, json=_MFR_ORDERS)
    return httpx.Response(404)


def _make_mfr_metrics_db(path: Path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE metrics (id INTEGER PRIMARY KEY, sim_day INTEGER, model_name TEXT, "
                 "finished_stock INTEGER, wholesale_price REAL, sales_orders_pending INTEGER, "
                 "sales_orders_completed INTEGER, production_utilisation REAL, parts_stock_json TEXT)")
    rows = [
        (1, 6, "P3D-Classic", 99, 1200.0, 0, 0, 0.5, '{"frame_kit": 999}'),   # older day, ignored
        (2, 7, "P3D-Classic", 12, 1200.0, 3, 2, 0.91, '{"frame_kit": 20, "pcb_control": 200}'),
        (3, 7, "P3D-Pro", 5, 246.0, 1, 4, 0.40, '{"frame_kit_pro": 15}'),
    ]
    conn.executemany("INSERT INTO metrics VALUES (?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()


def test_collect_manufacturer_uses_live_api(tmp_path):
    db = tmp_path / "manufacturer.db"
    _make_mfr_metrics_db(db)
    svc = ServiceConfig("Factory", "http://mfr", db)
    client = httpx.AsyncClient(transport=httpx.MockTransport(_mfr_handler))
    tier = asyncio.run(collect_tier("manufacturer", svc, client))
    asyncio.run(client.aclose())

    assert tier["online"] is True and tier["current_day"] == 7
    # finished models from /api/inventory
    classic = next(i for i in tier["items"] if i["name"] == "P3D-Classic")
    assert classic["kind"] == "finished" and classic["stock"] == 12.0 and classic["price"] == 1200.0
    # raw parts from /api/inventory (unit_type == "raw")
    frame = next(i for i in tier["items"] if i["name"] == "frame_kit")
    assert frame["kind"] == "part" and frame["stock"] == 20 and frame["price"] is None
    # utilisation still from metrics table (not in /api/inventory)
    assert tier["extra"]["utilisation_pct"] == 91.0   # max(0.91, 0.40) * 100
    # pending/completed counts from /api/orders
    assert tier["extra"]["sales_pending"] == 1 and tier["extra"]["sales_completed"] == 1
    assert tier["in_transit_out"] is None
    # orders list from /api/orders
    assert any(o["id"] == 10 and o["label"] == "P3D-Classic" for o in tier["orders"])


def test_collect_manufacturer_online_without_metrics_db(tmp_path):
    svc = ServiceConfig("Factory", "http://mfr", tmp_path / "missing.db")
    client = httpx.AsyncClient(transport=httpx.MockTransport(_mfr_handler))
    tier = asyncio.run(collect_tier("manufacturer", svc, client))
    asyncio.run(client.aclose())
    assert tier["online"] is True
    assert [i["name"] for i in tier["items"] if i["kind"] == "finished"] == ["P3D-Classic", "P3D-Pro"]
    assert tier["extra"]["utilisation_pct"] is None  # no metrics DB → no util


def test_collect_tier_offline_when_unreachable():
    svc = ServiceConfig("Down", "http://down", Path("x.db"))

    def boom(request):
        raise httpx.ConnectError("nope", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(boom))
    tier = asyncio.run(collect_tier("provider", svc, client))
    asyncio.run(client.aclose())
    assert tier["online"] is False
    assert tier["items"] == [] and tier["orders"] == []
