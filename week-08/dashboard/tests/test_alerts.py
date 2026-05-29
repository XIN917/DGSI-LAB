from dashboard.alerts import compute_alerts


def _tier(items, online=True, extra=None):
    return {"online": online, "items": items, "orders": [], "extra": extra or {}}


def test_stockout_is_error():
    tiers = {"retailer": _tier([{"name": "P3D-Pro", "stock": 0, "capacity": 50}])}
    alerts = compute_alerts(tiers, backlog=9)
    assert any(a["level"] == "error" and "P3D-Pro" in a["text"] for a in alerts)
    assert any("9 backordered" in a["text"] for a in alerts)


def test_low_stock_is_warning_not_error():
    tiers = {"provider": _tier([{"name": "chip", "stock": 10, "capacity": 100}])}  # 10% <= 20%
    alerts = compute_alerts(tiers, backlog=0)
    levels = {a["level"] for a in alerts}
    assert "warning" in levels and "error" not in levels


def test_healthy_stock_no_alert():
    tiers = {"provider": _tier([{"name": "frame", "stock": 80, "capacity": 100}])}
    assert compute_alerts(tiers, backlog=0) == []


def test_high_production_util_warns():
    tiers = {"manufacturer": _tier([], extra={"utilisation_pct": 92.0})}
    alerts = compute_alerts(tiers, backlog=0)
    assert any("production" in a["text"].lower() for a in alerts)


def test_offline_tier_skipped():
    tiers = {"provider": _tier([{"name": "chip", "stock": 0, "capacity": 100}], online=False)}
    assert compute_alerts(tiers, backlog=0) == []
