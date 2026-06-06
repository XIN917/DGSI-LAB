HIGH_UTIL_PCT = 90.0
MAX_LISTED = 4  # cap on item names listed inside a grouped alert


def compute_alerts(tiers: dict, backlog: float) -> list[dict]:
    """Build the overview alert row.

    Ordered by urgency: production idle → out of stock → stalled orders →
    high utilisation. Zero-stock items are collapsed into a single alert so a
    late-run collapse (many parts at 0) reads as one signal, not a wall of rows.
    """
    alerts: list[dict] = []
    out_of_stock: list[str] = []
    util_alerts: list[dict] = []

    for tier_name, tier in tiers.items():
        if not tier.get("online", False):
            continue
        for item in tier.get("items", []):
            if item.get("stock", 0) == 0:
                out_of_stock.append(f"{tier_name.capitalize()} {item['name']}")
        util = tier.get("extra", {}).get("utilisation_pct")
        if util is not None and util >= HIGH_UTIL_PCT:
            util_alerts.append({"level": "warning", "text": f"{tier_name.capitalize()} production {util:.0f}%"})

    # production idle while orders are waiting — the real crisis signal
    mfr_util = tiers.get("manufacturer", {}).get("extra", {}).get("utilisation_pct")
    if mfr_util is not None and mfr_util <= 0 and backlog and backlog > 0:
        alerts.append({"level": "error", "text": "production idle with open backlog"})

    # all zero-stock items collapsed into one alert
    if out_of_stock:
        shown = ", ".join(out_of_stock[:MAX_LISTED])
        more = len(out_of_stock) - MAX_LISTED
        if more > 0:
            shown += f" +{more} more"
        alerts.append({"level": "error", "text": f"{len(out_of_stock)} out of stock: {shown}"})

    # retailer orders stalled at the manufacturer for lack of materials
    stalled = tiers.get("retailer", {}).get("extra", {}).get("stalled") or 0
    if stalled > 0:
        alerts.append({"level": "warning", "text": f"{int(stalled)} units stalled at manufacturer"})

    alerts.extend(util_alerts)
    return alerts
