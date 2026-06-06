from dashboard.alerts import compute_alerts


def _tier(items=None, online=True, extra=None):
    return {"online": online, "items": items or [], "orders": [], "extra": extra or {}}


def _texts(alerts):
    return [a["text"] for a in alerts]


def test_healthy_stock_no_alert():
    tiers = {"provider": _tier([{"name": "frame", "stock": 80}]),
             "manufacturer": _tier(extra={"utilisation_pct": 60}),
             "retailer": _tier(extra={"stalled": 0})}
    assert compute_alerts(tiers, backlog=0) == []


def test_stockout_is_error_and_grouped():
    # a single zero-stock item still produces one grouped "out of stock" error
    tiers = {"retailer": _tier([{"name": "P3D-Pro", "stock": 0}])}
    alerts = compute_alerts(tiers, backlog=9)
    assert any(a["level"] == "error" and "out of stock" in a["text"] and "P3D-Pro" in a["text"]
               for a in alerts)


def test_many_stockouts_collapse_to_one_alert_with_overflow():
    items = [{"name": f"p{i}", "stock": 0} for i in range(6)]
    alerts = compute_alerts({"provider": _tier(items)}, backlog=0)
    stock_alerts = [a for a in alerts if "out of stock" in a["text"]]
    assert len(stock_alerts) == 1
    assert stock_alerts[0]["text"].startswith("6 out of stock:")
    assert "+2 more" in stock_alerts[0]["text"]  # MAX_LISTED=4 listed, 2 elided


def test_no_backordered_alert():
    # backlog is shown in the KPI bar, not duplicated as an alert
    tiers = {"manufacturer": _tier(extra={"utilisation_pct": 50})}
    assert not any("backorder" in t for t in _texts(compute_alerts(tiers, backlog=9)))


def test_idle_production_with_backlog():
    tiers = {"manufacturer": _tier(extra={"utilisation_pct": 0})}
    assert "production idle with open backlog" in _texts(compute_alerts(tiers, backlog=4))
    # util 0 but no backlog → no idle alert
    assert "production idle with open backlog" not in _texts(compute_alerts(tiers, backlog=0))


def test_stalled_alert():
    tiers = {"retailer": _tier(extra={"stalled": 380})}
    assert "380 units stalled at manufacturer" in _texts(compute_alerts(tiers, backlog=0))


def test_high_production_util_warns():
    tiers = {"manufacturer": _tier(extra={"utilisation_pct": 92.0})}
    assert any("production" in t.lower() for t in _texts(compute_alerts(tiers, backlog=0)))


def test_offline_tier_skipped():
    tiers = {"provider": _tier([{"name": "chip", "stock": 0}], online=False)}
    assert compute_alerts(tiers, backlog=0) == []


def test_urgency_ordering_idle_before_stock_before_stalled():
    tiers = {"provider": _tier([{"name": "p", "stock": 0}]),
             "manufacturer": _tier(extra={"utilisation_pct": 0}),
             "retailer": _tier(extra={"stalled": 100})}
    texts = _texts(compute_alerts(tiers, backlog=3))
    assert texts.index("production idle with open backlog") < \
           next(i for i, t in enumerate(texts) if "out of stock" in t) < \
           next(i for i, t in enumerate(texts) if "stalled" in t)
