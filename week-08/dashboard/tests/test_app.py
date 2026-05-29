from pathlib import Path
import dashboard.app as appmod
from fastapi.testclient import TestClient


def _fake_tiers():
    return {
        "provider": {"online": True, "current_day": 14, "items": [{"name": "chip", "stock": 0, "capacity": None}],
                     "orders": [], "in_transit_out": 40, "extra": {}},
        "manufacturer": {"online": True, "current_day": 14, "items": [], "orders": [], "in_transit_out": None,
                         "extra": {"utilisation_pct": 91.0}},
        "retailer": {"online": True, "current_day": 14,
                     "items": [], "orders": [{"id": 1, "status": "backordered"}], "in_transit_out": 0, "extra": {}},
    }


def test_api_state_assembles_payload(monkeypatch):
    async def fake_collect(services):
        return _fake_tiers()

    monkeypatch.setattr(appmod, "collect_all", fake_collect)
    monkeypatch.setattr(appmod, "build_history", lambda services: {"provider": {"series": {}, "peak": {}}})
    monkeypatch.setattr(appmod, "load_context", lambda **kw: {
        "scenario": "holiday-rush", "day_total": 25,
        "latest": {"events": "Black Friday", "demand_mod": 2.0, "supply_mod": 0.5, "lead_mod": 1.0,
                   "fill_rate": 66.7, "backordered": 4, "day": 14},
        "fill_rate_series": [[14, 66.7]]})

    client = TestClient(appmod.create_app(Path("config/sim.json")))
    r = client.get("/api/state")
    assert r.status_code == 200
    data = r.json()
    assert data["day"] == 14 and data["day_total"] == 25 and data["scenario"] == "holiday-rush"
    assert data["kpis"]["fill_rate"] == 66.7
    assert data["kpis"]["backlog"] == 1           # one backordered retailer order
    assert data["kpis"]["production_util"] == 91.0
    assert any(a["level"] == "error" for a in data["alerts"])  # chip stock 0
    assert set(data["tiers"]) == {"provider", "manufacturer", "retailer"}


def test_pages_return_html(monkeypatch):
    async def fake_collect(services):
        return _fake_tiers()

    monkeypatch.setattr(appmod, "collect_all", fake_collect)
    client = TestClient(appmod.create_app(Path("config/sim.json")))
    for path in ["/", "/provider", "/manufacturer", "/retailer"]:
        r = client.get(path)
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
