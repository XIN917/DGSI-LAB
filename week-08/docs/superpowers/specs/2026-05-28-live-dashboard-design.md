# Live Supply Chain Dashboard — Design

**Date:** 2026-05-28
**Status:** Approved (design phase)
**Author:** David Morais (with Claude)

## 1. Purpose

A browser-based **live monitoring dashboard** for the three-service supply chain
simulation (Provider → Manufacturer → Retailer). It auto-refreshes while
`turn_engine.py` is running so you can watch the chain react in real time —
ideal for the demo video and for spotting cascading problems (stockouts,
bullwhip) as they happen.

It is **read-only**. It never mutates simulation state and never calls
`day advance`; it only reads.

This complements, and does not replace, `visualize.py` (post-run static charts).

## 2. Pages

A small Python web server serves one shared dark-themed shell with a top nav:

| Path | Page | Content |
|---|---|---|
| `/` | **Overview** | The pipeline view: KPI strip + 3 tier cards in a row with order-flow arrows + alert feed |
| `/provider` | **Provider deep-dive** | KPI tiles, stock bars, order list, trend charts |
| `/manufacturer` | **Manufacturer deep-dive** | same shell, manufacturer data |
| `/retailer` | **Retailer deep-dive** | same shell, retailer data |

All pages auto-refresh on a fixed interval (default **2s**, configurable).

### 2.1 Overview page

- **Status / KPI strip:** LIVE indicator, scenario name, current day (`Day 14`,
  or `Day 14 / 25` when the scenario file is found), fill-rate, total backlog,
  manufacturer capacity utilisation, and active event modifiers
  (e.g. `×2.0 dmd · ×0.5 sup`).
- **Pipeline:** three tier cards left→right (Provider, Manufacturer, Retailer)
  with arrows between them showing units currently **in transit** (open
  orders between tiers). Each card shows its headline figures + a small
  sparkline.
- **Alert feed:** a strip of computed warnings (stockouts, low stock, high
  capacity).

### 2.2 Detail pages (one per tier — same template)

Each detail page = **KPI tiles** + **detail panels** + **trend charts**:

- **KPI tiles** (4): tier-appropriate headline numbers.
- **Stock panel with bars:** one row per item — a horizontal bar showing
  *current stock vs capacity* (label `40 / 150` inside), with price and lead
  time as numbers on the right. Bar colour signals health
  (red ≤ low threshold, amber ≤ warning, green otherwise).
- **Orders panel as a list:** one readable row per order
  (`#312  chip ×40 — SHIPPED · ETA d16`), grouped/ordered by status.
- **Trend charts (larger):** full-width SVG line charts (~200px tall) of the
  per-day history for that tier, redrawn on every refresh so they grow live as
  days advance.

**Capacity reference for the stock bars:**
- **Manufacturer:** real warehouse capacity from `GET /api/inventory`
  (`capacity`, `usage_pct`).
- **Provider & Retailer:** no hard cap is exposed, so the bar scales against
  each item's **highest level seen so far in the run** (peak from the metrics
  history). The bar therefore reads as depletion-vs-peak.

**Per-tier detail content:**

- **Provider:** all parts (stock bar + tier-1 price + lead days), incoming
  orders from the manufacturer, per-part stock-over-time and price-over-time
  charts.
- **Manufacturer:** finished stock (Classic/Pro) + wholesale prices, raw-parts
  inventory + warehouse usage %, sales orders (with BOM requirements),
  production utilisation, purchase orders to the provider; charts for finished
  stock, wholesale price, and utilisation over time.
- **Retailer:** per-SKU stock + retail prices, customer orders
  (placed/fulfilled/backordered), fill-rate gauge + backlog, in-flight purchase
  orders to the manufacturer; charts for stock, retail price, and fill-rate over
  time.

## 3. Data sources

The dashboard combines three read-only sources, each updating live during a run:

1. **Live HTTP polls of the 3 services** (current snapshot — intra-day real
   time). Service URLs come from `config/sim.json`. Read-only GET endpoints
   already exist:
   - Provider: `GET /api/day/current`, `/api/stock/`, `/api/catalog/`, `/api/orders/`
   - Manufacturer: `GET /api/day/current`, `/api/catalog` (both public).
     **Note:** `/api/inventory` and `/api/orders` require auth, and the dashboard
     uses no credentials — so the manufacturer's finished stock, raw parts,
     production utilisation, and sales-order counts are read from its no-auth
     per-day `metrics` table instead (see `latest_manufacturer_state` in
     `history.py`). Consequences: no per-order list and no warehouse
     capacity/usage for the manufacturer tile, and its data is empty until a run
     writes metrics.
   - Retailer: `GET /api/day/current`, `/api/inventory`, `/api/catalog`,
     `/api/customer-orders`
2. **The `metrics` table in each service DB** (per-day history for the trend
   charts and for the provider/retailer bar peaks). Same source `visualize.py`
   uses (`provider/data/provider.db`, etc.). Read with stdlib `sqlite3`.
   - provider.metrics: `sim_day, product_name, stock_quantity, price_tier1, orders_pending, orders_shipped, orders_delivered`
   - manufacturer.metrics: `sim_day, model_name, finished_stock, wholesale_price, sales_orders_pending, sales_orders_completed, production_utilisation, parts_stock_json`
   - retailer.metrics: `sim_day, sku, stock_quantity, retail_price, orders_placed, orders_fulfilled, orders_backordered`
3. **`logs/run.csv`** (latest row — scenario name + active event modifiers +
   fill-rate for the overview strip). Read with stdlib `csv`. Columns:
   `scenario, day, demand_mod, supply_mod, lead_mod, price_sensitivity, events,
   orders_placed, fulfilled, backordered, stockout, fill_rate_pct`.

**Graceful degradation (boundary handling):** each source is optional. If a
service is unreachable, that tier renders as `offline` (greyed) and the rest
keep working. If a DB is missing/locked, its trend charts are simply omitted.
If `run.csv` is absent, the scenario/event overlay is hidden and fill-rate is
computed from the retailer's customer-orders instead. The dashboard never
crashes because the sim isn't running yet.

## 4. Architecture

```
dashboard.py                  # entrypoint: `python dashboard.py [--port 8000] [--refresh 2] [--config config/sim.json]`
dashboard/                    # backend package
├── __init__.py
├── app.py            # FastAPI app + routes (/, /provider, /manufacturer, /retailer, /api/state); serves frontend/
├── config.py         # load config/sim.json → service URLs + db paths
├── collector.py      # async httpx polls of the 3 services → live snapshot (per tier, with offline flags); manufacturer auth
├── history.py        # read metrics tables from the 3 DBs → per-day series + per-item peaks
├── context.py        # read logs/run.csv latest row (+ optional scenario file) → scenario/day-total/events
├── alerts.py         # pure function: snapshot → list[alert] via thresholds
└── tests/            # pytest suite for the above
frontend/                     # frontend assets (top-level folder, served at /static + as the shell)
├── index.html        # nav shell + mount point + bootstrap (page type + refresh interval)
├── dashboard.css     # dark theme
└── dashboard.js      # fetch /api/state every N s; render overview or a detail page; draw SVG charts
```

### 4.1 Request flow

- `GET /`, `/provider`, `/manufacturer`, `/retailer` → serve `shell.html` with a
  `data-page` attribute and the configured refresh interval. The page type
  selects which view `dashboard.js` renders.
- `GET /api/state` → JSON assembled fresh on each call:
  ```jsonc
  {
    "day": 14,
    "day_total": 25,            // null if scenario file not found
    "scenario": "holiday-rush", // null if run.csv absent
    "events": {"label": "Black Friday + chip shortage",
               "demand_mod": 2.0, "supply_mod": 0.5, "lead_mod": 1.0},
    "kpis": {"fill_rate": 67, "backlog": 9, "capacity_util": 91},
    "alerts": [{"level": "error", "text": "Retailer Pro stock 0 (9 backordered)"}],
    "tiers": {
      "provider":     {"online": true, "items": [...], "orders": [...], "history": {...}},
      "manufacturer": {"online": true, "items": [...], "orders": [...], "capacity": {...}, "history": {...}},
      "retailer":     {"online": true, "items": [...], "orders": [...], "history": {...}}
    }
  }
  ```
- `dashboard.js` polls `/api/state` on `setInterval` and re-renders without a
  full page reload, so tables, bars, lists, and charts update smoothly in real
  time.

### 4.2 Charts

Hand-drawn **SVG** line charts in vanilla JS (no chart library, no CDN — works
offline). Larger than the mockup sparklines (~full-width × ~200px), with y-axis
min/max scaling, a few labelled ticks, a legend, and a "today" marker. Each
series is one `<polyline>`; redrawn from the `history` payload every refresh.

### 4.3 Dependencies

Reuses what the project already has: **fastapi**, **uvicorn**, **httpx** (used
by the services). Standard library for `sqlite3` and `csv` — **no pandas, no
chart library, no new heavy deps**. Can run from the manufacturer venv (already
has these) or its own.

## 5. Components & responsibilities

| Unit | Does | Depends on |
|---|---|---|
| `config.py` | Parse `config/sim.json`; resolve service URLs + db paths | sim.json |
| `collector.py` | Concurrently GET live state from 3 services; normalise to a snapshot; flag offline tiers | httpx, config |
| `history.py` | Query `metrics` tables → per-day series + per-item peaks | sqlite3, config |
| `context.py` | Last `run.csv` row → scenario/events/fill-rate; optional scenario-file day total | csv |
| `alerts.py` | Pure: snapshot → alerts via thresholds (low stock, stockout+demand, high util, backorders) | — |
| `app.py` | Wire the above into `/api/state`; serve pages + static | fastapi, all above |
| `dashboard.js` | Poll `/api/state`; render overview/detail; draw SVG charts | — |

Each is independently testable; `alerts.py`, `history.py`, `context.py` are pure
data-in/data-out.

## 6. Error handling

Only at boundaries (the design trusts internal code):
- Per-service poll wrapped in try/except + timeout → `online: false` on failure.
- DB read guarded for missing file / locked / missing table → omit that history.
- `run.csv` / scenario file guarded for absence → overlay hidden, KPI fallback.
- `/api/state` always returns 200 with whatever could be gathered.

## 7. Testing

- **`alerts.py`** — snapshots → expected alert lists (thresholds, edge cases:
  zero stock, exactly-at-threshold, all healthy).
- **`history.py`** — seed a temp SQLite with a known `metrics` table → assert
  series + peak extraction; assert graceful handling of missing table/file.
- **`context.py`** — temp `run.csv` → assert latest-row parsing; assert
  behaviour with missing file and with a single header-only file.
- **`collector.py`** — `httpx.MockTransport` simulating the 3 services →
  assert normalised snapshot; simulate one service down → `online: false`.
- **`app.py`** — FastAPI `TestClient` with a stubbed collector: `/api/state`
  returns 200 + expected keys; `/`, `/provider`, `/manufacturer`, `/retailer`
  return HTML 200.

Manual: start the services, start `dashboard.py`, run a few calm-market days,
confirm pages update live in the browser and degrade cleanly when a service is
stopped.

## 8. Out of scope (YAGNI)

- No write/control actions (no triggering runs, no editing prices) — read-only.
- No auth, no multi-user, no persistence of dashboard state.
- No replacement of `visualize.py` post-run charts.
- No historical scenario comparison (that was the Post-Run Analytics concept,
  not chosen).

## 9. Open question (non-blocking)

`day_total` ("/ 25") requires mapping the running scenario name to
`scenarios/<name>.json` to read its length. If that mapping is missing the
header just shows `Day 14`. Acceptable.
