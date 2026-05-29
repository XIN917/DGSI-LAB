LOW_STOCK_FRACTION = 0.20
HIGH_UTIL_PCT = 90.0


def compute_alerts(tiers: dict, backlog: float) -> list[dict]:
    alerts: list[dict] = []
    for tier_name, tier in tiers.items():
        if not tier.get("online", False):
            continue
        for item in tier.get("items", []):
            cap = item.get("capacity")
            stock = item.get("stock", 0)
            label = f"{tier_name.capitalize()} {item['name']}"
            if stock == 0:
                alerts.append({"level": "error", "text": f"{label} stock 0"})
            elif cap and stock <= cap * LOW_STOCK_FRACTION:
                alerts.append({"level": "warning", "text": f"{label} low ({int(stock)})"})
        util = tier.get("extra", {}).get("utilisation_pct")
        if util is not None and util >= HIGH_UTIL_PCT:
            alerts.append({"level": "warning", "text": f"{tier_name.capitalize()} production {util:.0f}%"})
    if backlog and backlog > 0:
        alerts.append({"level": "error" if backlog >= 5 else "warning",
                       "text": f"{int(backlog)} backordered"})
    return alerts
