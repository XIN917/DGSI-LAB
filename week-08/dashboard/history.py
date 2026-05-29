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
