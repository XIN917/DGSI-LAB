import asyncio
import httpx
from dashboard.config import ServiceConfig
from dashboard.history import latest_manufacturer_state, manufacturer_parts_from_inventory, latest_manufacturer_orders
from dashboard import derive

OFFLINE = {"online": False, "current_day": None, "items": [], "orders": [], "in_transit_out": 0, "extra": {}}
PROVIDER_OPEN = {"SHIPPED"}


async def _get_json(client: httpx.AsyncClient, url: str):
    r = await client.get(url, timeout=8.0)
    r.raise_for_status()
    return r.json()


def _tier1_price(pricing_tiers: list) -> float | None:
    if not pricing_tiers:
        return None
    raw = min(pricing_tiers, key=lambda t: t["min_quantity"])["unit_price"]
    try:
        return float(raw)
    except (TypeError, ValueError):
        return raw


BUSY = {"online": True, "current_day": None, "items": [], "orders": [], "in_transit_out": 0, "extra": {}, "busy": True}

async def collect_tier(tier: str, svc: ServiceConfig, client: httpx.AsyncClient) -> dict:
    try:
        if tier == "provider":
            return await _collect_provider(svc, client)
        if tier == "manufacturer":
            return await _collect_manufacturer(svc, client)
        return await _collect_retailer(svc, client)
    except httpx.TimeoutException:
        return dict(BUSY)
    except (httpx.HTTPError, KeyError, ValueError):
        return dict(OFFLINE)


async def _collect_provider(svc, client):
    base = svc.url
    day, stock, catalog, orders = await asyncio.gather(
        _get_json(client, f"{base}/api/day/current"),
        _get_json(client, f"{base}/api/stock/"),
        _get_json(client, f"{base}/api/catalog/"),
        _get_json(client, f"{base}/api/orders/"))
    by_id = {c["id"]: c for c in catalog}
    qty = {s["product_id"]: s["quantity"] for s in stock}
    items = []
    for c in catalog:
        items.append({"name": c["name"], "stock": qty.get(c["id"], 0), "capacity": None,
                      "price": _tier1_price(c.get("pricing_tiers", [])),
                      "lead": c.get("lead_time_days"), "kind": "part"})
    in_transit = sum(o["quantity"] for o in orders if o.get("status") in PROVIDER_OPEN)
    out_orders = sorted([{"id": o["id"], "label": by_id.get(o["product_id"], {}).get("name", str(o["product_id"])),
                   "qty": o["quantity"], "status": o.get("status", ""),
                   "eta": o.get("expected_delivery_day")} for o in orders],
                  key=lambda x: x["id"], reverse=True)
    return {"online": True, "current_day": day["current_day"], "items": items,
            "orders": out_orders, "in_transit_out": in_transit, "extra": {}}


async def _collect_manufacturer(svc, client):
    base = svc.url
    day, catalog, inv, orders = await asyncio.gather(
        _get_json(client, f"{base}/api/day/current"),
        _get_json(client, f"{base}/api/catalog"),
        _get_json(client, f"{base}/api/inventory"),
        _get_json(client, f"{base}/api/orders"))
    inv_by_name = {i["product_name"]: i for i in inv.get("items", [])}
    items = []
    for c in catalog:
        inv_item = inv_by_name.get(c["sku"], inv_by_name.get(c["name"], {}))
        stock = inv_item.get("quantity", 0)
        items.append({"name": c["sku"], "stock": stock, "capacity": None,
                      "price": c["unit_price"], "lead": None, "kind": "finished"})
    finished_names = {i["name"] for i in items}
    parts = {name: int(i["quantity"]) for name, i in inv_by_name.items()
             if i.get("unit_type") == "raw"}
    for pname, qty in derive.dedup_parts(parts, finished_names).items():
        items.append({"name": pname, "stock": qty, "capacity": None,
                      "price": None, "lead": None, "kind": "part"})
    pending = sum(1 for o in orders if o["status"] in {"pending", "in_progress", "waiting_materials"})
    completed = sum(1 for o in orders if o["status"] == "completed")
    state = latest_manufacturer_state(svc.db_path)
    util_pct = round(state["util"] * 100, 1) if state and state["util"] is not None else None
    out_orders = [{"id": o["id"], "label": o["product_model"],
                   "qty": int(o["quantity_needed"]), "qty_produced": int(o["quantity_produced"]),
                   "status": o["status"], "eta": o.get("delivery_day")}
                  for o in orders[:500]]
    return {"online": True, "current_day": day["current_day"], "items": items,
            "orders": out_orders,
            # pending sales orders are NOT goods in transit — the manufacturer→retailer
            # arrow is driven by the retailer's incoming POs. Pending stays in extra.
            "in_transit_out": None,
            "extra": {"utilisation_pct": util_pct,
                      "sales_pending": pending,
                      "sales_completed": completed}}


async def _collect_retailer(svc, client):
    base = svc.url
    day, inv, catalog, orders, purchase_orders = await asyncio.gather(
        _get_json(client, f"{base}/api/day/current"),
        _get_json(client, f"{base}/api/inventory"),
        _get_json(client, f"{base}/api/catalog"),
        _get_json(client, f"{base}/api/customer-orders"),
        _get_json(client, f"{base}/api/purchase-orders"))
    items = [{"name": i["sku"], "sku": i["sku"], "stock": i["quantity_on_hand"],
              "capacity": None, "price": i.get("retail_price"), "lead": None, "kind": "sku"} for i in inv]
    out_orders = sorted([{"id": o["id"], "label": o["sku"], "qty": o["quantity"],
                   "status": o.get("status", ""), "eta": o.get("fulfilled_day")} for o in orders],
                  key=lambda x: x["id"], reverse=True)
    return {"online": True, "current_day": day["current_day"], "items": items, "orders": out_orders,
            "in_transit_out": derive.retailer_in_transit(purchase_orders),
            "extra": {"stalled": derive.retailer_stalled(purchase_orders)}}


async def collect_all(services: dict[str, ServiceConfig]) -> dict:
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[collect_tier(t, s, client) for t, s in services.items()])
    return dict(zip(services.keys(), results))
