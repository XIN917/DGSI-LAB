# Live Supply Chain Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only, auto-refreshing browser dashboard that polls the three running services live and shows an Overview pipeline page plus a deep-dive page per tier.

**Architecture:** A small FastAPI app (`dashboard/`) reads service URLs + DB paths from `config/sim.json`. On each `GET /api/state` it concurrently polls the three services (live snapshot), reads each service's `metrics` table (per-day history for charts), and reads `logs/run.csv` (scenario/events overlay). A vanilla-JS frontend polls `/api/state` on an interval and re-renders without a full reload, drawing SVG trend charts. Read-only: it never mutates state or advances days.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, httpx (all already in the project), stdlib `sqlite3` + `csv`, vanilla JS + hand-drawn SVG (no chart library, no CDN). Tests run with the manufacturer venv.

**Spec:** `docs/superpowers/specs/2026-05-28-live-dashboard-design.md`

---

## Data Contracts (referenced by multiple tasks)

**Service config** (`config.py` output) — one entry per tier:
```python
# dict: tier -> ServiceConfig
{"provider":     ServiceConfig(name="ChipSupply",   url="http://127.0.0.1:8001", db_path=Path("provider/data/provider.db")),
 "manufacturer": ServiceConfig(name="Factory",      url="http://127.0.0.1:8002", db_path=Path("manufacturer/data/manufacturer.db")),
 "retailer":     ServiceConfig(name="PrinterWorld", url="http://127.0.0.1:8003", db_path=Path("retailer/data/retailer.db"))}
```

**Normalized tier snapshot** (`collector.py` output, per tier):
```python
{
  "online": bool,
  "current_day": int | None,
  "items": [ {"name": str, "stock": float, "capacity": float | None,
              "price": float | None, "lead": int | None, "kind": str} ],   # kind: "part"|"finished"|"sku"
  "orders": [ {"id": int, "label": str, "qty": float, "status": str, "eta": int | None} ],
  "in_transit_out": float,   # units flowing to the next tier (open orders); retailer = 0
  "extra": dict,             # tier-specific (manufacturer: {"total_units","capacity","usage_pct"})
}
```

**History** (`history.py` output, per tier):
```python
{ "series": { "<metric>": { "<key>": [[day, value], ...] } },   # e.g. series["stock"]["chip"] = [[1,150],[2,120]]
  "peak":   { "<key>": float } }                                # max stock seen per item, for bar scaling
```

**Context** (`context.py` output):
```python
{ "scenario": str | None, "day_total": int | None,
  "latest": {"events": str, "demand_mod": float, "supply_mod": float,
             "lead_mod": float, "fill_rate": float, "backordered": int, "day": int} | None,
  "fill_rate_series": [[day, fill_rate_pct], ...] }
```

**`/api/state` payload** (`app.py` output): `{day, day_total, scenario, events, kpis, alerts, tiers, history}` where `tiers` maps each tier → its normalized snapshot, `history` maps each tier → its history, `events` = context `latest` modifiers, `kpis` = `{fill_rate, backlog, capacity_util}`.

**Test command (all tasks):**
```bash
PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/ -v
```

---

## Task 1: Package scaffold + config loader

**Files:**
- Create: `dashboard/__init__.py` (empty)
- Create: `dashboard/tests/__init__.py` (empty)
- Create: `dashboard/config.py`
- Test: `dashboard/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# dashboard/tests/test_config.py
import json
from pathlib import Path
from dashboard.config import load_services, ServiceConfig

def test_load_services_maps_three_tiers(tmp_path):
    sim = {
        "retailers": [{"name": "PrinterWorld", "url": "http://127.0.0.1:8003", "path": "./retailer"}],
        "manufacturer": {"name": "Factory", "url": "http://127.0.0.1:8002", "path": "./manufacturer"},
        "providers": [{"name": "ChipSupply", "url": "http://127.0.0.1:8001", "path": "./provider"}],
    }
    cfg = tmp_path / "sim.json"
    cfg.write_text(json.dumps(sim))

    services = load_services(cfg)

    assert set(services) == {"provider", "manufacturer", "retailer"}
    assert services["provider"] == ServiceConfig(
        name="ChipSupply", url="http://127.0.0.1:8001", db_path=Path("provider/data/provider.db"))
    assert services["manufacturer"].url == "http://127.0.0.1:8002"
    assert services["retailer"].db_path == Path("retailer/data/retailer.db")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dashboard.config'`

- [ ] **Step 3: Write minimal implementation**

```python
# dashboard/config.py
import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ServiceConfig:
    name: str
    url: str
    db_path: Path

def _db_path(tier: str, entry: dict) -> Path:
    base = Path(entry.get("path", f"./{tier}").lstrip("./"))
    return base / "data" / f"{tier}.db"

def load_services(sim_json_path: Path) -> dict[str, ServiceConfig]:
    data = json.loads(Path(sim_json_path).read_text())
    provider = data["providers"][0]
    retailer = data["retailers"][0]
    manufacturer = data["manufacturer"]
    return {
        "provider": ServiceConfig(provider["name"], provider["url"].rstrip("/"), _db_path("provider", provider)),
        "manufacturer": ServiceConfig(manufacturer["name"], manufacturer["url"].rstrip("/"), _db_path("manufacturer", manufacturer)),
        "retailer": ServiceConfig(retailer["name"], retailer["url"].rstrip("/"), _db_path("retailer", retailer)),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dashboard/__init__.py dashboard/tests/__init__.py dashboard/config.py dashboard/tests/test_config.py
git commit -m "feat(dashboard): add package scaffold and sim.json config loader"
```

---

## Task 2: Scenario/run.csv context reader

**Files:**
- Create: `dashboard/context.py`
- Test: `dashboard/tests/test_context.py`

- [ ] **Step 1: Write the failing test**

```python
# dashboard/tests/test_context.py
import json
from dashboard.context import load_context

RUN_CSV = (
    "scenario,day,demand_mod,supply_mod,lead_mod,price_sensitivity,events,orders_placed,fulfilled,backordered,stockout,fill_rate_pct\n"
    "holiday-rush,13,1.0,1.0,1.0,1.0,Black Friday,10,9,1,0,90.0\n"
    "holiday-rush,14,2.0,0.5,1.0,1.0,Black Friday + chip shortage,12,8,4,0,66.7\n"
)

def test_load_context_reads_latest_row_and_series(tmp_path):
    run_csv = tmp_path / "run.csv"
    run_csv.write_text(RUN_CSV)
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    (scenarios / "holiday-rush.json").write_text(json.dumps({
        "events": [{"start_day": 1, "end_day": 25, "demand_modifier": 1.0, "supply_modifier": 1.0}]}))

    ctx = load_context(run_csv=run_csv, scenarios_dir=scenarios)

    assert ctx["scenario"] == "holiday-rush"
    assert ctx["day_total"] == 25
    assert ctx["latest"]["fill_rate"] == 66.7
    assert ctx["latest"]["backordered"] == 4
    assert ctx["latest"]["demand_mod"] == 2.0
    assert ctx["latest"]["events"] == "Black Friday + chip shortage"
    assert ctx["fill_rate_series"] == [[13, 90.0], [14, 66.7]]

def test_load_context_missing_file_is_graceful(tmp_path):
    ctx = load_context(run_csv=tmp_path / "nope.csv", scenarios_dir=tmp_path)
    assert ctx == {"scenario": None, "day_total": None, "latest": None, "fill_rate_series": []}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_context.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dashboard.context'`

- [ ] **Step 3: Write minimal implementation**

```python
# dashboard/context.py
import csv
import json
from pathlib import Path

_EMPTY = {"scenario": None, "day_total": None, "latest": None, "fill_rate_series": []}

def _day_total(scenarios_dir: Path, scenario: str) -> int | None:
    f = Path(scenarios_dir) / f"{scenario}.json"
    if not f.exists():
        return None
    try:
        events = json.loads(f.read_text()).get("events", [])
        return max((int(e["end_day"]) for e in events), default=None)
    except (ValueError, KeyError):
        return None

def load_context(run_csv: Path, scenarios_dir: Path) -> dict:
    run_csv = Path(run_csv)
    if not run_csv.exists():
        return dict(_EMPTY)
    with run_csv.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return dict(_EMPTY)
    scenario = rows[-1]["scenario"]
    scenario_rows = [r for r in rows if r["scenario"] == scenario]
    last = scenario_rows[-1]
    series = [[int(r["day"]), float(r["fill_rate_pct"])] for r in scenario_rows]
    latest = {
        "events": last.get("events", ""),
        "demand_mod": float(last["demand_mod"]),
        "supply_mod": float(last["supply_mod"]),
        "lead_mod": float(last["lead_mod"]),
        "fill_rate": float(last["fill_rate_pct"]),
        "backordered": int(last["backordered"]),
        "day": int(last["day"]),
    }
    return {"scenario": scenario, "day_total": _day_total(scenarios_dir, scenario),
            "latest": latest, "fill_rate_series": series}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_context.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add dashboard/context.py dashboard/tests/test_context.py
git commit -m "feat(dashboard): read scenario/run.csv context with graceful fallback"
```

---

## Task 3: Metrics-table history reader

**Files:**
- Create: `dashboard/history.py`
- Test: `dashboard/tests/test_history.py`

- [ ] **Step 1: Write the failing test**

```python
# dashboard/tests/test_history.py
import sqlite3
from pathlib import Path
from dashboard.history import read_provider_history

def _make_provider_db(path: Path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE metrics (id INTEGER PRIMARY KEY, sim_day INTEGER, product_id INTEGER, "
                 "product_name TEXT, stock_quantity INTEGER, price_tier1 REAL, orders_pending INTEGER, "
                 "orders_shipped INTEGER, orders_delivered INTEGER)")
    rows = [(1, 1, 1, "chip", 150, 12.0, 0, 0, 0),
            (2, 2, 1, "chip", 120, 12.0, 1, 0, 0),
            (3, 1, 2, "frame", 80, 30.0, 0, 0, 0)]
    conn.executemany("INSERT INTO metrics VALUES (?,?,?,?,?,?,?,?,?)", rows)
    conn.commit(); conn.close()

def test_read_provider_history_series_and_peak(tmp_path):
    db = tmp_path / "provider.db"
    _make_provider_db(db)

    hist = read_provider_history(db)

    assert hist["series"]["stock"]["chip"] == [[1, 150], [2, 120]]
    assert hist["series"]["price"]["chip"] == [[1, 12.0], [2, 12.0]]
    assert hist["peak"]["chip"] == 150
    assert hist["peak"]["frame"] == 80

def test_read_provider_history_missing_db_is_graceful(tmp_path):
    hist = read_provider_history(tmp_path / "nope.db")
    assert hist == {"series": {}, "peak": {}}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_history.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dashboard.history'`

- [ ] **Step 3: Write minimal implementation**

```python
# dashboard/history.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_history.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add dashboard/history.py dashboard/tests/test_history.py
git commit -m "feat(dashboard): read per-day metrics history for trend charts"
```

---

## Task 4: Alerts (pure function)

**Files:**
- Create: `dashboard/alerts.py`
- Test: `dashboard/tests/test_alerts.py`

- [ ] **Step 1: Write the failing test**

```python
# dashboard/tests/test_alerts.py
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

def test_high_capacity_util_warns():
    tiers = {"manufacturer": _tier([], extra={"usage_pct": 92.0})}
    alerts = compute_alerts(tiers, backlog=0)
    assert any("capacity" in a["text"].lower() for a in alerts)

def test_offline_tier_skipped():
    tiers = {"provider": _tier([{"name": "chip", "stock": 0, "capacity": 100}], online=False)}
    assert compute_alerts(tiers, backlog=0) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_alerts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dashboard.alerts'`

- [ ] **Step 3: Write minimal implementation**

```python
# dashboard/alerts.py
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
        usage = tier.get("extra", {}).get("usage_pct")
        if usage is not None and usage >= HIGH_UTIL_PCT:
            alerts.append({"level": "warning", "text": f"{tier_name.capitalize()} capacity {usage:.0f}%"})
    if backlog and backlog > 0:
        alerts.append({"level": "error" if backlog >= 5 else "warning",
                       "text": f"{int(backlog)} backordered"})
    return alerts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_alerts.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add dashboard/alerts.py dashboard/tests/test_alerts.py
git commit -m "feat(dashboard): compute live alerts from a tier snapshot"
```

---

## Task 5: Live collector (async httpx polling + normalization)

**Files:**
- Create: `dashboard/collector.py`
- Test: `dashboard/tests/test_collector.py`

**Notes on normalization (from real endpoint shapes):**
- Provider stock (`GET /api/stock/`) returns `{product_id, quantity}` with NO name → join with catalog (`GET /api/catalog/` → `{id, name, lead_time_days, pricing_tiers:[{min_quantity, unit_price}]}`). Price = `unit_price` of the tier with the smallest `min_quantity`. Provider has no per-part capacity → `capacity=None`.
- Provider orders (`GET /api/orders/`): open = status in `{PENDING, CONFIRMED, SHIPPED}`; `in_transit_out` = sum of their `quantity`.
- Manufacturer inventory (`GET /api/inventory`) → object with `items:[{product_name, quantity, max_capacity}]`, `total_units`, `capacity`, `usage_pct`. Catalog (`GET /api/catalog`) → `[{sku, name, unit_price}]` (wholesale). Finished items = inventory items whose `product_name` matches a catalog `name`/`sku`; rest = parts. Orders (`GET /api/orders`) status in `{pending, released, waiting_materials}` are open; `in_transit_out` = sum `quantity_needed`.
- Retailer inventory (`GET /api/inventory`) → `[{sku, quantity_on_hand, retail_price}]`; catalog (`GET /api/catalog`) → `[{sku, name, retail_price}]`. No capacity → `None`. Orders (`GET /api/customer-orders`) status values `{pending, fulfilled, backordered, cancelled}`; backlog handled by app, retailer `in_transit_out=0`.
- All `GET /api/day/current` → `{"current_day": int}`.

- [ ] **Step 1: Write the failing test**

```python
# dashboard/tests/test_collector.py
import asyncio
import json
import httpx
from dashboard.collector import collect_tier
from dashboard.config import ServiceConfig
from pathlib import Path

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

def test_collect_tier_offline_when_unreachable():
    svc = ServiceConfig("Down", "http://down", Path("x.db"))
    def boom(request): raise httpx.ConnectError("nope", request=request)
    client = httpx.AsyncClient(transport=httpx.MockTransport(boom))
    tier = asyncio.run(collect_tier("provider", svc, client))
    asyncio.run(client.aclose())
    assert tier["online"] is False
    assert tier["items"] == [] and tier["orders"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_collector.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dashboard.collector'`

- [ ] **Step 3: Write minimal implementation**

```python
# dashboard/collector.py
import asyncio
import httpx
from dashboard.config import ServiceConfig

OFFLINE = {"online": False, "current_day": None, "items": [], "orders": [], "in_transit_out": 0, "extra": {}}
PROVIDER_OPEN = {"PENDING", "CONFIRMED", "SHIPPED"}
MFR_OPEN = {"pending", "released", "waiting_materials"}

async def _get_json(client: httpx.AsyncClient, url: str):
    r = await client.get(url, timeout=3.0)
    r.raise_for_status()
    return r.json()

def _tier1_price(pricing_tiers: list) -> float | None:
    if not pricing_tiers:
        return None
    return min(pricing_tiers, key=lambda t: t["min_quantity"])["unit_price"]

async def collect_tier(tier: str, svc: ServiceConfig, client: httpx.AsyncClient) -> dict:
    try:
        if tier == "provider":
            return await _collect_provider(svc, client)
        if tier == "manufacturer":
            return await _collect_manufacturer(svc, client)
        return await _collect_retailer(svc, client)
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
    out_orders = [{"id": o["id"], "label": by_id.get(o["product_id"], {}).get("name", str(o["product_id"])),
                   "qty": o["quantity"], "status": o.get("status", ""),
                   "eta": o.get("expected_delivery_day")} for o in orders]
    return {"online": True, "current_day": day["current_day"], "items": items,
            "orders": out_orders, "in_transit_out": in_transit, "extra": {}}

async def _collect_manufacturer(svc, client):
    base = svc.url
    day, inv, catalog, orders = await asyncio.gather(
        _get_json(client, f"{base}/api/day/current"),
        _get_json(client, f"{base}/api/inventory"),
        _get_json(client, f"{base}/api/catalog"),
        _get_json(client, f"{base}/api/orders"))
    price_by_name = {c["name"]: c["unit_price"] for c in catalog}
    price_by_sku = {c["sku"]: c["unit_price"] for c in catalog}
    finished_names = set(price_by_name) | set(price_by_sku)
    items = []
    for it in inv.get("items", []):
        name = it["product_name"]
        is_finished = name in finished_names
        items.append({"name": name, "stock": it["quantity"], "capacity": it.get("max_capacity"),
                      "price": price_by_name.get(name) or price_by_sku.get(name) if is_finished else None,
                      "lead": None, "kind": "finished" if is_finished else "part"})
    in_transit = sum(o.get("quantity_needed", 0) for o in orders if o.get("status") in MFR_OPEN)
    out_orders = [{"id": o["id"], "label": o.get("product_model", ""), "qty": o.get("quantity_needed", 0),
                   "status": o.get("status", ""), "eta": o.get("delivery_day")} for o in orders]
    return {"online": True, "current_day": day["current_day"], "items": items, "orders": out_orders,
            "in_transit_out": in_transit,
            "extra": {"total_units": inv.get("total_units"), "capacity": inv.get("capacity"),
                      "usage_pct": inv.get("usage_pct")}}

async def _collect_retailer(svc, client):
    base = svc.url
    day, inv, catalog, orders = await asyncio.gather(
        _get_json(client, f"{base}/api/day/current"),
        _get_json(client, f"{base}/api/inventory"),
        _get_json(client, f"{base}/api/catalog"),
        _get_json(client, f"{base}/api/customer-orders"))
    name_by_sku = {c["sku"]: c["name"] for c in catalog}
    items = [{"name": name_by_sku.get(i["sku"], i["sku"]), "sku": i["sku"], "stock": i["quantity_on_hand"],
              "capacity": None, "price": i.get("retail_price"), "lead": None, "kind": "sku"} for i in inv]
    out_orders = [{"id": o["id"], "label": o["sku"], "qty": o["quantity"],
                   "status": o.get("status", ""), "eta": o.get("fulfilled_day")} for o in orders]
    return {"online": True, "current_day": day["current_day"], "items": items, "orders": out_orders,
            "in_transit_out": 0, "extra": {}}

async def collect_all(services: dict[str, ServiceConfig]) -> dict:
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[collect_tier(t, s, client) for t, s in services.items()])
    return dict(zip(services.keys(), results))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_collector.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add dashboard/collector.py dashboard/tests/test_collector.py
git commit -m "feat(dashboard): async live collector normalizing the three services"
```

---

## Task 6: FastAPI app — /api/state assembly + page routes

**Files:**
- Create: `dashboard/app.py`
- Test: `dashboard/tests/test_app.py`

- [ ] **Step 1: Write the failing test**

```python
# dashboard/tests/test_app.py
from pathlib import Path
import dashboard.app as appmod
from fastapi.testclient import TestClient

def _fake_tiers():
    return {
        "provider": {"online": True, "current_day": 14, "items": [{"name": "chip", "stock": 0, "capacity": None}],
                     "orders": [], "in_transit_out": 40, "extra": {}},
        "manufacturer": {"online": True, "current_day": 14, "items": [], "orders": [], "in_transit_out": 30,
                         "extra": {"usage_pct": 91.0}},
        "retailer": {"online": True, "current_day": 14,
                     "items": [], "orders": [{"id": 1, "status": "backordered"}], "in_transit_out": 0, "extra": {}},
    }

def test_api_state_assembles_payload(monkeypatch):
    async def fake_collect(services): return _fake_tiers()
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
    assert data["kpis"]["capacity_util"] == 91.0
    assert any(a["level"] == "error" for a in data["alerts"])  # chip stock 0
    assert set(data["tiers"]) == {"provider", "manufacturer", "retailer"}

def test_pages_return_html(monkeypatch):
    monkeypatch.setattr(appmod, "collect_all", lambda services: _fake_tiers())
    client = TestClient(appmod.create_app(Path("config/sim.json")))
    for path in ["/", "/provider", "/manufacturer", "/retailer"]:
        r = client.get(path)
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dashboard.app'`

- [ ] **Step 3: Write minimal implementation**

```python
# dashboard/app.py
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from dashboard.config import load_services
from dashboard.collector import collect_all
from dashboard.history import (read_provider_history, read_manufacturer_history, read_retailer_history)
from dashboard.context import load_context
from dashboard.alerts import compute_alerts

_DIR = Path(__file__).parent
_PAGES = {"/": "overview", "/provider": "provider", "/manufacturer": "manufacturer", "/retailer": "retailer"}

def build_history(services) -> dict:
    return {
        "provider": read_provider_history(services["provider"].db_path),
        "manufacturer": read_manufacturer_history(services["manufacturer"].db_path),
        "retailer": read_retailer_history(services["retailer"].db_path),
    }

def _render_shell(page: str, refresh: int) -> str:
    html = (_DIR / "templates" / "shell.html").read_text()
    return html.replace("{{PAGE}}", page).replace("{{REFRESH}}", str(refresh))

def create_app(sim_json_path: Path, refresh: int = 2) -> FastAPI:
    services = load_services(sim_json_path)
    app = FastAPI(title="Supply Chain Live Dashboard")
    app.mount("/static", StaticFiles(directory=_DIR / "static"), name="static")

    @app.get("/api/state")
    async def api_state():
        tiers = await collect_all(services)
        ctx = load_context(run_csv=Path("logs/run.csv"), scenarios_dir=Path("scenarios"))
        backlog = sum(1 for o in tiers["retailer"]["orders"] if o.get("status") == "backordered")
        day = max((t["current_day"] for t in tiers.values() if t.get("current_day") is not None), default=None)
        latest = ctx.get("latest") or {}
        fill_rate = latest.get("fill_rate")
        usage = tiers["manufacturer"]["extra"].get("usage_pct")
        return JSONResponse({
            "day": day, "day_total": ctx.get("day_total"), "scenario": ctx.get("scenario"),
            "events": {"label": latest.get("events"), "demand_mod": latest.get("demand_mod"),
                       "supply_mod": latest.get("supply_mod"), "lead_mod": latest.get("lead_mod")},
            "kpis": {"fill_rate": fill_rate, "backlog": backlog, "capacity_util": usage},
            "alerts": compute_alerts(tiers, backlog),
            "tiers": tiers, "history": build_history(services),
            "fill_rate_series": ctx.get("fill_rate_series", []),
        })

    for route, page in _PAGES.items():
        async def page_handler(_page=page):
            return HTMLResponse(_render_shell(_page, refresh))
        app.get(route)(page_handler)

    return app
```

- [ ] **Step 4: Run test to verify it passes**

Note: `test_pages_return_html` needs `dashboard/templates/shell.html` and `dashboard/static/` to exist. Create stubs now so this task is self-contained; Tasks 7–8 fill them in:

```bash
mkdir -p dashboard/templates dashboard/static
printf '<!DOCTYPE html><html><body data-page="{{PAGE}}" data-refresh="{{REFRESH}}"></body></html>' > dashboard/templates/shell.html
printf '/* placeholder */\n' > dashboard/static/dashboard.css
printf '// placeholder\n' > dashboard/static/dashboard.js
```

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_app.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add dashboard/app.py dashboard/tests/test_app.py dashboard/templates/shell.html dashboard/static/dashboard.css dashboard/static/dashboard.js
git commit -m "feat(dashboard): FastAPI app assembling /api/state and serving pages"
```

---

## Task 7: HTML shell + nav

**Files:**
- Modify: `dashboard/templates/shell.html` (replace placeholder)

- [ ] **Step 1: Write the shell**

Replace the entire file with:

```html
<!-- dashboard/templates/shell.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Supply Chain · Live</title>
  <link rel="stylesheet" href="/static/dashboard.css">
</head>
<body data-page="{{PAGE}}" data-refresh="{{REFRESH}}">
  <nav class="topnav">
    <div class="navlinks">
      <a href="/" data-nav="overview">Overview</a>
      <a href="/provider" data-nav="provider">Provider</a>
      <a href="/manufacturer" data-nav="manufacturer">Manufacturer</a>
      <a href="/retailer" data-nav="retailer">Retailer</a>
    </div>
    <div id="livebadge" class="live">● connecting…</div>
  </nav>
  <main id="root"><p class="muted">Loading…</p></main>
  <script src="/static/dashboard.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verify app tests still pass**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_app.py -v`
Expected: PASS (2 tests — pages still return HTML)

- [ ] **Step 3: Commit**

```bash
git add dashboard/templates/shell.html
git commit -m "feat(dashboard): html shell with tier navigation"
```

---

## Task 8: Dark theme CSS

**Files:**
- Modify: `dashboard/static/dashboard.css` (replace placeholder)

- [ ] **Step 1: Write the stylesheet**

Replace the entire file with:

```css
/* dashboard/static/dashboard.css */
:root{--bg:#0f172a;--panel:#111827;--line:#334155;--muted:#64748b;--text:#e2e8f0;
  --accent:#38bdf8;--ok:#34d399;--warn:#fbbf24;--err:#f87171;--mfr:#a78bfa;--ret:#f472b6;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}
.topnav{display:flex;justify-content:space-between;align-items:center;padding:10px 16px;background:#0b1120;border-bottom:1px solid var(--line);position:sticky;top:0}
.navlinks a{color:var(--muted);text-decoration:none;padding:5px 12px;border-radius:6px;margin-right:4px}
.navlinks a.active{background:#1e293b;color:var(--accent);font-weight:bold}
.live{color:var(--ok)} .live.down{color:var(--err)}
main{padding:16px;max-width:1200px;margin:0 auto}
.muted{color:var(--muted)}
.kpibar{display:flex;gap:14px;flex-wrap:wrap;align-items:center;border-bottom:1px solid var(--line);padding-bottom:10px;margin-bottom:14px}
.kpibar b{color:var(--warn)}
.tiles{display:flex;gap:8px;margin-bottom:14px}
.tile{flex:1;background:var(--panel);border-radius:8px;padding:10px;text-align:center}
.tile .big{font-size:20px;font-weight:bold}
.pipeline{display:flex;align-items:stretch;gap:8px}
.card{flex:1;border:1px solid var(--line);border-radius:8px;padding:12px;background:rgba(17,24,39,.4)}
.card h3{margin:0 0 8px;border-bottom:1px solid #1e293b;padding-bottom:6px}
.card.provider h3{color:var(--accent)} .card.manufacturer h3{color:var(--mfr)} .card.retailer h3{color:var(--ret)}
.card.offline{opacity:.45}
.arrow{align-self:center;text-align:center;color:var(--warn);min-width:54px}
.arrow .n{font-size:16px;font-weight:bold}
.panel{border:1px solid var(--line);border-radius:8px;padding:12px;margin-top:12px;background:rgba(17,24,39,.4)}
.panel h3{margin:0 0 10px;color:var(--accent)}
.stockrow{display:flex;align-items:center;margin:4px 0;gap:8px}
.stockrow .name{width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar{flex:1;background:#1e293b;border-radius:4px;height:16px;position:relative}
.bar .fill{position:absolute;left:0;top:0;height:16px;border-radius:4px}
.bar .lbl{position:absolute;left:6px;top:0;line-height:16px;font-size:11px}
.fill.ok{background:var(--ok)} .fill.warn{background:var(--warn)} .fill.err{background:var(--err)}
.num{width:60px;text-align:right}
.orderlist .o{display:flex;justify-content:space-between;padding:6px 8px;border-radius:5px;background:var(--panel);margin-bottom:4px}
.status-shipped,.status-released,.status-pending{color:var(--warn)}
.status-delivered,.status-fulfilled,.status-completed{color:var(--ok)}
.status-backordered,.status-failed{color:var(--err)}
.alerts{margin-top:14px;border-top:1px solid var(--line);padding-top:8px}
.alerts .a{margin-right:14px}
.a.error{color:var(--err)} .a.warning{color:var(--warn)}
.charts{display:flex;gap:12px;flex-wrap:wrap;margin-top:12px}
.chart{flex:1 1 360px;border:1px solid var(--line);border-radius:8px;padding:10px}
.chart h4{margin:0 0 6px;color:var(--muted);font-weight:normal}
.chart svg{width:100%;height:200px;display:block}
.legend{display:flex;gap:12px;flex-wrap:wrap;margin-top:6px;font-size:11px;color:var(--muted)}
.legend span::before{content:"";display:inline-block;width:10px;height:3px;margin-right:4px;vertical-align:middle;background:currentColor}
.sparkline{height:24px;width:100%}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/static/dashboard.css
git commit -m "feat(dashboard): dark theme stylesheet"
```

---

## Task 9: Frontend core — fetch loop + Overview render

**Files:**
- Modify: `dashboard/static/dashboard.js` (replace placeholder; this task writes the shared core + overview)

- [ ] **Step 1: Write the JS core + overview**

Replace the entire file with:

```javascript
// dashboard/static/dashboard.js
const PAGE = document.body.dataset.page;
const REFRESH = (parseInt(document.body.dataset.refresh, 10) || 2) * 1000;
const TIER_COLORS = {provider:"#38bdf8", manufacturer:"#a78bfa", retailer:"#f472b6"};
const root = document.getElementById("root");
const badge = document.getElementById("livebadge");

document.querySelectorAll("[data-nav]").forEach(a => {
  if (a.dataset.nav === PAGE) a.classList.add("active");
});

function barClass(stock, cap){
  if (stock === 0) return "err";
  if (cap && stock <= cap * 0.20) return "warn";
  return "ok";
}
function pct(stock, cap, peak){
  const max = cap || peak || stock || 1;
  return Math.max(2, Math.min(100, (stock / max) * 100));
}
function fmt(n){ return n == null ? "–" : (Number.isInteger(n) ? n : Number(n).toFixed(1)); }
function statusClass(s){ return "status-" + String(s || "").toLowerCase(); }

async function tick(){
  try {
    const res = await fetch("/api/state");
    const data = await res.json();
    const d = data.day == null ? "–" : data.day;
    const dt = data.day_total ? ` / ${data.day_total}` : "";
    badge.textContent = `● LIVE · ${data.scenario || "no scenario"} · Day ${d}${dt}`;
    badge.classList.remove("down");
    render(data);
  } catch (e) {
    badge.textContent = "● disconnected — is the dashboard server running?";
    badge.classList.add("down");
  }
}

function render(data){
  if (PAGE === "overview") renderOverview(data);
  else renderDetail(PAGE, data);  // defined in Task 10
}

function renderOverview(data){
  const k = data.kpis, ev = data.events || {};
  const tierCard = (name, tier) => {
    if (!tier.online) return `<div class="card ${name} offline"><h3>${name.toUpperCase()}</h3><p class="muted">offline</p></div>`;
    const top = tier.items.slice(0, 3).map(i =>
      `<div>${i.name} <b>${fmt(i.stock)}</b></div>`).join("");
    const extra = name === "manufacturer" && tier.extra.usage_pct != null
      ? `<div class="muted">util ${fmt(tier.extra.usage_pct)}%</div>` : "";
    return `<div class="card ${name}"><h3>${name.toUpperCase()}</h3>${top}${extra}
      <svg class="sparkline" data-spark="${name}"></svg></div>`;
  };
  const arrow = (n) => `<div class="arrow">▶▶<div class="n">${fmt(n)}</div><div class="muted">in transit</div></div>`;
  root.innerHTML = `
    <div class="kpibar">
      <span>fill-rate <b>${fmt(k.fill_rate)}%</b></span>
      <span>backlog <b>${fmt(k.backlog)}</b></span>
      <span>capacity util <b>${fmt(k.capacity_util)}%</b></span>
      ${ev.demand_mod != null ? `<span>events <b>×${ev.demand_mod} dmd · ×${ev.supply_mod} sup</b></span>` : ""}
    </div>
    <div class="pipeline">
      ${tierCard("provider", data.tiers.provider)}
      ${arrow(data.tiers.provider.in_transit_out)}
      ${tierCard("manufacturer", data.tiers.manufacturer)}
      ${arrow(data.tiers.manufacturer.in_transit_out)}
      ${tierCard("retailer", data.tiers.retailer)}
    </div>
    <div class="alerts">
      <span class="muted">ALERTS&nbsp;&nbsp;</span>
      ${data.alerts.length ? data.alerts.map(a => `<span class="a ${a.level}">⚠ ${a.text}</span>`).join(" · ")
                            : '<span class="muted">none</span>'}
    </div>`;
  // mini sparklines: first stock series per tier
  ["provider","manufacturer","retailer"].forEach(name => {
    const svg = root.querySelector(`[data-spark="${name}"]`);
    const hist = (data.history[name] || {}).series || {};
    const stockSeries = hist.stock || hist.finished_stock || {};
    const first = Object.values(stockSeries)[0];
    if (svg && first) drawSparkline(svg, first, TIER_COLORS[name]);  // defined in Task 11
  });
}

setInterval(tick, REFRESH);
tick();
```

- [ ] **Step 2: Manual smoke check (no services needed yet)**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/python -c "import ast; ast.parse(open('dashboard/static/dashboard.js').read()) if False else print('js written')"`
Then verify the file has no obvious syntax error by opening `http://127.0.0.1:8000` after Task 12 (the badge should show "disconnected" gracefully when no services run). Functions `renderDetail` and `drawSparkline` are added in Tasks 10–11; until then the overview page renders the KPI bar and pipeline shell.
Expected: file saved; overview renders without throwing (detail/chart helpers land next).

- [ ] **Step 3: Commit**

```bash
git add dashboard/static/dashboard.js
git commit -m "feat(dashboard): frontend fetch loop and overview pipeline render"
```

---

## Task 10: Frontend — detail page render (stock bars + order list)

**Files:**
- Modify: `dashboard/static/dashboard.js` (append `renderDetail` + helpers)

- [ ] **Step 1: Append detail rendering**

Add to the end of `dashboard/static/dashboard.js` (before the final `setInterval`/`tick` lines — place these function definitions above them, or append and rely on hoisting since they are `function` declarations):

```javascript
function kpiTiles(name, tier){
  const items = tier.items || [];
  const total = items.reduce((s, i) => s + (i.stock || 0), 0);
  const low = items.filter(i => i.capacity && i.stock <= i.capacity * 0.20).length
            + items.filter(i => i.stock === 0).length;
  const pending = (tier.orders || []).filter(o => /pending|released|shipped|waiting/i.test(o.status)).length;
  if (name === "manufacturer"){
    return tileRow([["finished models", items.filter(i=>i.kind==="finished").length],
      ["warehouse used", fmt(tier.extra.total_units)], ["capacity", fmt(tier.extra.capacity)],
      ["util %", fmt(tier.extra.usage_pct)]]);
  }
  return tileRow([["items", items.length], ["total units", fmt(total)],
    ["low / out", low], ["orders open", pending]]);
}
function tileRow(pairs){
  return `<div class="tiles">${pairs.map(([l,v]) =>
    `<div class="tile">${l}<div class="big">${v}</div></div>`).join("")}</div>`;
}
function stockPanel(name, tier, hist){
  const peak = (hist || {}).peak || {};
  const rows = (tier.items || []).map(i => {
    const cls = barClass(i.stock, i.capacity);
    const width = pct(i.stock, i.capacity, peak[i.name]);
    const cap = i.capacity ? `/ ${fmt(i.capacity)}` : (peak[i.name] ? `/ ${fmt(peak[i.name])}` : "");
    return `<div class="stockrow"><span class="name">${i.name}</span>
      <span class="bar"><span class="fill ${cls}" style="width:${width}%"></span>
        <span class="lbl">${fmt(i.stock)} ${cap}</span></span>
      <span class="num">${i.price != null ? "€"+fmt(i.price) : ""}</span>
      <span class="num">${i.lead != null ? i.lead+"d" : ""}</span></div>`;
  }).join("");
  return `<div class="panel"><h3>STOCK · CATALOG · PRICE</h3>${rows || '<p class="muted">no items</p>'}</div>`;
}
function orderPanel(name, tier){
  const title = {provider:"ORDERS (from Manufacturer)", manufacturer:"SALES ORDERS (from Retailer)",
                 retailer:"CUSTOMER ORDERS"}[name];
  const rows = (tier.orders || []).slice(0, 25).map(o => {
    const eta = o.eta != null ? ` · ${name==="retailer"?"fulfilled d":"ETA d"}${o.eta}` : "";
    return `<div class="o"><span><b>#${o.id}</b> &nbsp; ${o.label} ×${fmt(o.qty)}</span>
      <span class="${statusClass(o.status)}">${(o.status||"").toUpperCase()}${eta}</span></div>`;
  }).join("");
  return `<div class="panel orderlist"><h3>${title}</h3>${rows || '<p class="muted">no orders</p>'}</div>`;
}
function renderDetail(name, data){
  const tier = data.tiers[name];
  if (!tier || !tier.online){
    root.innerHTML = `<p class="muted">${name} is offline — start the service and the simulation.</p>`;
    return;
  }
  const hist = data.history[name] || {};
  root.innerHTML = kpiTiles(name, tier) + stockPanel(name, tier, hist)
    + orderPanel(name, tier) + chartsBlock(name, hist, data);  // chartsBlock defined in Task 11
  drawAllCharts(name, hist, data);  // defined in Task 11
}
```

- [ ] **Step 2: Verify file parses and app tests still pass**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/test_app.py -v`
Expected: PASS (serving unaffected). Chart helpers (`chartsBlock`, `drawAllCharts`) are added in Task 11; detail pages will fully render after that.

- [ ] **Step 3: Commit**

```bash
git add dashboard/static/dashboard.js
git commit -m "feat(dashboard): detail page render with stock bars and order lists"
```

---

## Task 11: Frontend — larger SVG trend charts

**Files:**
- Modify: `dashboard/static/dashboard.js` (append chart helpers)

- [ ] **Step 1: Append chart functions**

Add to the end of `dashboard/static/dashboard.js`:

```javascript
const PALETTE = ["#38bdf8","#a78bfa","#f472b6","#34d399","#fbbf24","#f87171","#22d3ee","#c084fc"];

function _bounds(seriesMap){
  let minX=Infinity,maxX=-Infinity,minY=Infinity,maxY=-Infinity;
  Object.values(seriesMap).forEach(pts => pts.forEach(([x,y]) => {
    minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}));
  if(!isFinite(minX))return null;
  if(minY>0)minY=0; if(maxY===minY)maxY=minY+1;
  return {minX,maxX,minY,maxY};
}
function _lineChart(svg, seriesMap){
  const W=svg.clientWidth||600, H=svg.clientHeight||200, pad={l:38,r:10,t:10,b:22};
  const b=_bounds(seriesMap);
  svg.innerHTML="";
  if(!b){ svg.innerHTML=`<text x="10" y="20" fill="#64748b">no history yet</text>`; return []; }
  const sx=x=>pad.l+((x-b.minX)/Math.max(1,b.maxX-b.minX))*(W-pad.l-pad.r);
  const sy=y=>H-pad.b-((y-b.minY)/(b.maxY-b.minY))*(H-pad.t-pad.b);
  const ns="http://www.w3.org/2000/svg";
  // y ticks
  [b.minY,(b.minY+b.maxY)/2,b.maxY].forEach(v=>{
    const t=document.createElementNS(ns,"text");t.setAttribute("x",2);t.setAttribute("y",sy(v)+4);
    t.setAttribute("fill","#475569");t.setAttribute("font-size","10");t.textContent=Math.round(v);svg.appendChild(t);
    const g=document.createElementNS(ns,"line");g.setAttribute("x1",pad.l);g.setAttribute("x2",W-pad.r);
    g.setAttribute("y1",sy(v));g.setAttribute("y2",sy(v));g.setAttribute("stroke","#1e293b");svg.appendChild(g);
  });
  const legend=[];
  Object.entries(seriesMap).forEach(([key,pts],idx)=>{
    const color=PALETTE[idx%PALETTE.length];legend.push([key,color]);
    const d=pts.map(([x,y],i)=>`${i?"L":"M"}${sx(x).toFixed(1)},${sy(y).toFixed(1)}`).join(" ");
    const pl=document.createElementNS(ns,"path");pl.setAttribute("d",d);pl.setAttribute("fill","none");
    pl.setAttribute("stroke",color);pl.setAttribute("stroke-width","1.8");svg.appendChild(pl);
  });
  return legend;
}
function drawSparkline(svg, pts, color){
  const W=svg.clientWidth||160,H=svg.clientHeight||24;
  const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);
  const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys,minY+1);
  const sx=x=>((x-minX)/Math.max(1,maxX-minX))*W, sy=y=>H-((y-minY)/(maxY-minY))*H;
  const d=pts.map((p,i)=>`${i?"L":"M"}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join(" ");
  svg.innerHTML=`<path d="${d}" fill="none" stroke="${color}" stroke-width="1.5"/>`;
}
function _chartDefs(name, data){
  if(name==="provider") return [["Stock over time (per part)","stock"],["Tier-1 price over time","price"]];
  if(name==="manufacturer") return [["Finished stock","finished_stock"],["Wholesale price","wholesale_price"],
    ["Production utilisation %","utilisation"]];
  return [["Stock over time (per SKU)","stock"],["Retail price over time","retail_price"],["__fill__","fill"]];
}
function chartsBlock(name, hist, data){
  const defs=_chartDefs(name,data);
  return `<div class="charts">`+defs.map(([title],i)=>
    `<div class="chart"><h4>${title==="__fill__"?"Fill-rate % over time":title}</h4>
      <svg data-chart="${i}"></svg><div class="legend" data-legend="${i}"></div></div>`).join("")+`</div>`;
}
function drawAllCharts(name, hist, data){
  const defs=_chartDefs(name,data);
  defs.forEach(([title,metric],i)=>{
    const svg=root.querySelector(`[data-chart="${i}"]`);if(!svg)return;
    let seriesMap;
    if(metric==="fill") seriesMap=data.fill_rate_series.length?{"fill-rate":data.fill_rate_series}:{};
    else seriesMap=(hist.series||{})[metric]||{};
    const legend=_lineChart(svg, seriesMap);
    const box=root.querySelector(`[data-legend="${i}"]`);
    if(box) box.innerHTML=legend.map(([k,c])=>`<span style="color:${c}">${k}</span>`).join("");
  });
}
```

- [ ] **Step 2: Verify app tests still pass and JS is complete**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/ -v`
Expected: PASS (all tests). The JS now defines every function referenced in Tasks 9–10 (`renderDetail`, `drawSparkline`, `chartsBlock`, `drawAllCharts`).

- [ ] **Step 3: Commit**

```bash
git add dashboard/static/dashboard.js
git commit -m "feat(dashboard): larger SVG trend charts with axes and legends"
```

---

## Task 12: Root entrypoint `dashboard.py`

**Files:**
- Create: `dashboard.py` (repo root)

- [ ] **Step 1: Write the entrypoint**

```python
# dashboard.py
import argparse
from pathlib import Path
import uvicorn
from dashboard.app import create_app

def main():
    parser = argparse.ArgumentParser(description="Live supply chain dashboard")
    parser.add_argument("--config", default="config/sim.json", help="path to sim.json")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--refresh", type=int, default=2, help="browser refresh interval (seconds)")
    args = parser.parse_args()
    app = create_app(Path(args.config), refresh=args.refresh)
    print(f"Dashboard → http://{args.host}:{args.port}  (config: {args.config}, refresh: {args.refresh}s)")
    uvicorn.run(app, host=args.host, port=args.port, reload=False, log_level="warning")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test it boots**

Run:
```bash
PYTHONPATH=. ./manufacturer/venv/bin/python -c "from pathlib import Path; from dashboard.app import create_app; create_app(Path('config/sim.json')); print('app builds OK')"
```
Expected: `app builds OK` (no exception).

- [ ] **Step 3: Commit**

```bash
git add dashboard.py
git commit -m "feat(dashboard): cli entrypoint to run the dashboard server"
```

---

## Task 13: Docs + full manual verification

**Files:**
- Modify: `README.md` (add a "Live Dashboard" section)
- Modify: `CLAUDE.md` (note the dashboard under Project Structure / how to run)

- [ ] **Step 1: Add README section**

Insert after the "Visualize Results" section (after its closing code block, before "### 6. Running Tests"):

```markdown
### 5b. Live Dashboard (real-time)

While a simulation is running, watch the chain live in your browser:

```bash
# In a separate terminal (services must be running)
PYTHONPATH=. ./manufacturer/venv/bin/python dashboard.py
# then open http://127.0.0.1:8000
```

Read-only. Polls the three services on an interval (default 2s; `--refresh N`).
Pages: Overview (pipeline) and a deep-dive per tier (Provider / Manufacturer /
Retailer) with stock-vs-capacity bars, order lists, and trend charts. It degrades
gracefully when a service or the simulation isn't running yet.
```

- [ ] **Step 2: Add CLAUDE.md note**

Add under the Project Structure tree (after the `visualize.py` line context), a one-line entry:

```markdown
├── dashboard.py       # Live read-only browser dashboard (polls all 3 services)
├── dashboard/         # Dashboard package (FastAPI app, collector, history, alerts, static, templates)
```

- [ ] **Step 3: Run the full dashboard test suite**

Run: `PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/ -v`
Expected: PASS (all tests across config/context/history/alerts/collector/app).

- [ ] **Step 4: Manual end-to-end verification (golden path + degradation)**

```bash
./scripts/reset_all.sh                      # fresh services on :8001/:8002/:8003
# terminal A:
PYTHONPATH=. ./manufacturer/venv/bin/python dashboard.py
# terminal B:
python turn_engine.py config/sim.json scenarios/calm-market.json 5
```
In the browser at `http://127.0.0.1:8000`:
- [ ] Live badge shows the scenario + advancing day.
- [ ] Overview pipeline shows three online tier cards, in-transit arrows, alert feed.
- [ ] Each detail page shows KPI tiles, stock bars (manufacturer bars scale to real capacity), order lists, and trend charts that grow as days advance.
- [ ] Stop one service (`kill` its uvicorn) → that tier shows "offline", others keep updating (graceful degradation).
- [ ] Before any run / empty DBs → charts show "no history yet" rather than erroring.

Note in the PR description anything that looked off; per project philosophy, do not rewind a run to make the dashboard look cleaner.

- [ ] **Step 5: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: document the live dashboard"
```

---

## Self-Review (completed during planning)

- **Spec coverage:** Overview page (Task 9), detail pages + bars + order lists (Tasks 10–11), three data sources — live polls (Task 5), metrics history (Task 3), run.csv context (Task 2) — assembled in `/api/state` (Task 6); alerts (Task 4); larger real-time charts (Task 11); read-only entrypoint (Task 12); graceful degradation (Tasks 2/3/5 fallbacks + Task 13 manual check); docs (Task 13). All spec sections mapped.
- **Placeholder scan:** Task 6 creates real stub files only so its tests can run; Tasks 7–11 replace them with full implementations. No "TBD/handle errors appropriately" left; every code step shows complete code.
- **Type consistency:** Normalized tier shape (`online/current_day/items/orders/in_transit_out/extra`) is identical across collector output (Task 5), alerts input (Task 4), app assembly (Task 6), and frontend consumers (Tasks 9–11). History shape (`series`/`peak`) matches between Task 3 producers and Task 11 consumers. `compute_alerts(tiers, backlog)` signature matches the call in Task 6.
```
