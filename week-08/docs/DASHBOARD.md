# Dashboard — Design Notes

Browser-based monitoring dashboard at `:8080`. Proxies data from `api_server.py` (:8000) and the three services. See `README.md` for startup instructions.

## Architecture

- `dashboard/app.py` — proxies `/api/sim/*` calls to `api_server.py` and exposes `/api/state` from service DBs directly
- `dashboard/collector.py` — reads from live service HTTP APIs and archived SQLite DBs
- `dashboard/context.py` — builds `event_summary` from scenario JSON
- `frontend/dashboard.js` — SVG charts drawn client-side; no PNG charts fetched for the live view

## API Server Endpoints (`:8000`)

15 endpoints across 5 groups — see `docs/API.md` for full reference.

Reset endpoints:
- `POST /reset` — fires `scripts/reset_all.sh` in background; returns immediately
- `GET /reset/status` — returns `{status: "idle"|"running"|"done"|"error", output: "..."}`

## KPI Logic

- **Fill rate**: `total fulfilled / total orders` across all days in `run.csv` (matches `summary.log`). Suppressed at day 0.
- **Backlog**: cumulative backordered orders summed from `run.csv`, not DB snapshot (which resolves to 0 at end of run). Falls back to current order count when no CSV exists.
- **Provider in-transit**: counts only `SHIPPED` orders. `CONFIRMED` and `InProgress` are still at the provider.
- **Utilisation %**: sourced from the `metrics` table only — the only place it's recorded.

## Overview Page

- Prominent day counter, color-coded KPI tiles (green/yellow/red thresholds), alerts strip, pipeline flow diagram, per-service SVG sparklines.
- Provider tier cards: 3 lowest-stock parts. Manufacturer cards: finished goods only (parts hidden). Sparklines match shown items. Price drift (↑/↓) shown per item.
- Sparkline labels shown below when multiple series are present.
- Event strip above header: all non-normal events as chips with name, day range, demand mod, supply mod (supply in red when < 1).
- All KPIs suppressed at day 0 to avoid showing stale CSV data.

## Order Panels (all service pages)

- Status summary bar (counts by status) above a scrollable list (newest first, LIMIT 500).
- Manufacturer orders from `GET /api/orders`. Provider and retailer sorted DESC in `collector.py`.
- Status colors: confirmed (cyan), in progress (purple), waiting materials (orange).
- `fmtStatus` helper: `InProgress` → `IN PROGRESS`, `waiting_materials` → `WAITING MATERIALS`.
- Customer orders panel: max 280px scroll, scroll position preserved across 2s refreshes.

## Archive View

- VIEW dropdown in nav switches between live service data and completed scenario archives.
- Selecting a scenario loads `logs/{scenario}/*.db` and `logs/{scenario}/run.csv` via `GET /api/archive/{scenario}/state`.
- Selection persists across pages via `sessionStorage`. Archives survive resets.

## Simulation Page

- Scenario/model/days/start-day selections persist across page navigation via `sessionStorage`.
- Terminal output rendered by xterm.js — ANSI codes from Rich rendered natively.
- Rich console width set to 150 to fit the terminal area.
- Log dropdown auto-selects the first scenario that has logs.
- Run chips show day range (`d1–10`) and elapsed time (`4m 42s`); duration frozen at completion.
- Reset: `POST /api/sim/reset` returns immediately; frontend polls `GET /api/sim/reset/status` every 2s.

## Key Implementation Notes

- `markup=False` must NOT be set on the callback Console in `turn_engine.py` — breaks ANSI codes in xterm.js.
- Services launched by `scripts/start_services.sh` use `start_new_session=True` so they stay running when `api_server.py` restarts.
- Manufacturer parts stock falls back to the `inventory` table at day 0 when the `metrics` table is empty.
- Scenario log archives survive reset — only live DBs are cleared. Per-scenario `run.csv` cleared at start of each new run.
- `proxy_runs` has JSONDecodeError handling for empty `api_server` responses.
