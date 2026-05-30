import json
import sqlite3
from pathlib import Path


def _query(db_path: Path, sql: str) -> list[tuple]:
    db_path = Path(db_path)
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []


def read_provider_history(db_path: Path) -> dict:
    rows = _query(db_path, "SELECT sim_day, product_name, stock_quantity, price_tier1 FROM metrics ORDER BY sim_day")
    series = {"stock": {}, "price": {}}
    peak: dict[str, float] = {}
    for day, name, stock, price in rows:
        series["stock"].setdefault(name, []).append([day, stock])
        if price is not None:
            series["price"].setdefault(name, []).append([day, price])
        peak[name] = max(peak.get(name, 0), stock or 0)
    return {"series": series, "peak": peak} if rows else {"series": {}, "peak": {}}


def read_manufacturer_history(db_path: Path) -> dict:
    rows = _query(db_path, "SELECT sim_day, model_name, finished_stock, wholesale_price, production_utilisation, "
                           "parts_stock_json FROM metrics ORDER BY sim_day")
    series = {"finished_stock": {}, "wholesale_price": {}, "utilisation": {}, "parts": {}}
    peak: dict[str, float] = {}
    for day, model, fstock, price, util, parts_json in rows:
        series["finished_stock"].setdefault(model, []).append([day, fstock])
        if price is not None:
            series["wholesale_price"].setdefault(model, []).append([day, price])
        if util is not None:
            series["utilisation"].setdefault("util", []).append([day, round(util * 100, 1)])
        peak[model] = max(peak.get(model, 0), fstock or 0)
        if parts_json:
            try:
                for pname, qty in json.loads(parts_json).items():
                    series["parts"].setdefault(pname, []).append([day, qty])
                    peak[pname] = max(peak.get(pname, 0), qty or 0)
            except (ValueError, TypeError):
                pass
    return {"series": series, "peak": peak} if rows else {"series": {}, "peak": {}}


def latest_manufacturer_state(db_path: Path) -> dict | None:
    """Latest-day manufacturer snapshot from the (no-auth) metrics table.

    Used instead of the authenticated /api/inventory and /api/orders endpoints.
    Returns None when no metrics have been written yet (e.g. before day 1).
    """
    rows = _query(db_path, "SELECT model_name, finished_stock, wholesale_price, sales_orders_pending, "
                           "sales_orders_completed, production_utilisation, parts_stock_json FROM metrics "
                           "WHERE sim_day = (SELECT MAX(sim_day) FROM metrics)")
    if not rows:
        return None
    finished, parts = [], {}
    util = None
    pending = completed = 0
    for model, fstock, wprice, sp, sc, u, parts_json in rows:
        finished.append({"name": model, "stock": fstock, "price": wprice})
        pending += sp or 0
        completed += sc or 0
        if u is not None:
            util = max(util or 0.0, u)
        if parts_json:
            try:
                parts.update(json.loads(parts_json))
            except (ValueError, TypeError):
                pass
    return {"finished": finished, "parts": parts, "util": util,
            "pending": pending, "completed": completed}


def read_retailer_history(db_path: Path) -> dict:
    rows = _query(db_path, "SELECT sim_day, sku, stock_quantity, retail_price FROM metrics ORDER BY sim_day")
    series = {"stock": {}, "retail_price": {}}
    peak: dict[str, float] = {}
    for day, sku, stock, price in rows:
        series["stock"].setdefault(sku, []).append([day, stock])
        if price is not None:
            series["retail_price"].setdefault(sku, []).append([day, price])
        peak[sku] = max(peak.get(sku, 0), stock or 0)
    return {"series": series, "peak": peak} if rows else {"series": {}, "peak": {}}


def latest_provider_state(db_path: Path) -> tuple[list[dict], list[dict]]:
    rows = _query(db_path, "SELECT product_name, stock_quantity, price_tier1 "
                           "FROM metrics WHERE sim_day = (SELECT MAX(sim_day) FROM metrics)")
    in_transit_rows = _query(db_path,
                             "SELECT product_id, SUM(quantity) FROM orders "
                             "WHERE status IN ('PENDING','CONFIRMED','SHIPPED') GROUP BY product_id")
    in_transit_by_id = {pid: qty for pid, qty in in_transit_rows}
    prod_rows = _query(db_path, "SELECT id, name, lead_time_days FROM products")
    id_by_name = {name: pid for pid, name, _ in prod_rows}
    lead_by_name = {name: lead for _, name, lead in prod_rows}
    items = [{"name": name, "stock": stock, "price": price,
              "in_transit": in_transit_by_id.get(id_by_name.get(name), 0),
              "lead": lead_by_name.get(name), "kind": "part"}
             for name, stock, price in rows]
    order_rows = _query(db_path, "SELECT o.id, p.name, o.quantity, o.status, o.expected_delivery_day "
                                 "FROM orders o JOIN products p ON p.id = o.product_id ORDER BY o.id ASC")
    orders = [{"id": oid, "label": name, "qty": qty, "status": status, "eta": eta}
              for oid, name, qty, status, eta in order_rows]
    return items, orders


def latest_retailer_state(db_path: Path) -> list[dict]:
    rows = _query(db_path, "SELECT sku, stock_quantity, retail_price "
                           "FROM metrics WHERE sim_day = (SELECT MAX(sim_day) FROM metrics)")
    return [{"name": sku, "stock": stock, "price": price, "kind": "sku"}
            for sku, stock, price in rows]


def latest_retailer_orders(db_path: Path) -> list[dict]:
    rows = _query(db_path, "SELECT id, sku, quantity, status, fulfilled_day "
                           "FROM customer_orders ORDER BY id ASC LIMIT 100")
    return [{"id": oid, "label": sku, "qty": qty, "status": status, "eta": fulfilled_day}
            for oid, sku, qty, status, fulfilled_day in rows]
