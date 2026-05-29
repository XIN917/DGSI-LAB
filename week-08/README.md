# DGSI Week 8 — Supply Chain Simulation

Autonomous multi-agent supply chain for 3D printers. Three services (Provider, Manufacturer, Retailer) each driven by an LLM agent. A turn engine orchestrates them through simulated days. Scenarios inject market pressure.

---

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

---

## Quickstart

### 1. Install dependencies

```bash
./scripts/setup_envs.sh
```

### 2. Start all services

```bash
./scripts/start_all.sh
```

Services run in the background on:
- Provider: http://127.0.0.1:8001
- Manufacturer: http://127.0.0.1:8002
- Retailer: http://127.0.0.1:8003

Logs: `logs/provider.log`, `logs/manufacturer.log`, `logs/retailer.log`

### 3. Reset to Day 0

```bash
./scripts/reset_all.sh
```

Stops services, deletes all databases, re-seeds fresh state, and restarts services. Always reset before a new run or between different scenarios to ensure clean data.

### 4. Run a simulation

```bash
# Volatile 25-day run (Black Friday + chip shortage + Christmas)
python turn_engine.py config/sim.json scenarios/holiday-rush.json 25

# Calm 15-day baseline
python turn_engine.py config/sim.json scenarios/calm-market.json 15

# Switch LLM model with --model
python turn_engine.py config/sim.json scenarios/calm-market.json 15 --model <model_name>

# Full agent reasoning output (default: compact 3-line summary)
python turn_engine.py config/sim.json scenarios/calm-market.json 15 -v

# Resume/chunk a long run after session limits
python turn_engine.py config/sim.json scenarios/holiday-rush.json 25 --start-day 16

# Debug with the original full skill markdown instead of compact role contracts
python turn_engine.py config/sim.json scenarios/calm-market.json 15 --full-skill-prompt
```

Agent logs are saved to `logs/{scenario_name}/day-NNN.log`. Databases are automatically snapshotted to the same directory at the end of each run. KPI data is appended to `logs/run.csv`. Normal runs use compact role contracts and capped prefetch output to reduce token usage; pass `--full-skill-prompt` only when debugging agent behavior.

> **Note:** `manufacturer/providers.json` must exist and point to the provider URL (`http://127.0.0.1:8001`). It is tracked in git — if missing, manufacturer procurement will silently fail every day.
>
> **Note:** All three services run with `reload=False`. Do not change this — `reload=True` causes WatchFiles to restart the server mid-run if any file is edited, corrupting the manufacturer DB mid-simulation.
>
> **Note:** Manufacturer seed inventory for `frame_kit` is intentionally low (20 units) so the manufacturer agent is forced to order from the provider within the first few days. Do not raise it or the reorder behavior disappears in short runs.

### 5. Visualize Results

After a simulation run, generate multi-product charts with split-panel layouts to analyze supply chain dynamics. The visualizer works on archived folders even if `run.csv` is missing.

```bash
# Visualize all models and parts from recent runs
python visualize.py

# Visualize a specific archived folder (e.g. from demo/ or logs/)
python visualize.py demo/calm-market
python visualize.py logs/holiday-rush
```

### 5b. Live Dashboard (real-time)

Watch the chain react live in your browser while a simulation runs. Read-only —
it never mutates state or advances days.

```bash
# In a separate terminal, with the three services already running.
# Use a venv that has fastapi/uvicorn/httpx (the manufacturer venv does):
PYTHONPATH=. ./manufacturer/venv/bin/python dashboard.py
# then open http://127.0.0.1:8000

# Options:
#   --port 8000        port to serve on
#   --refresh 2        browser refresh interval in seconds
#   --config config/sim.json   where to read service URLs from
```

Pages: **Overview** (pipeline with KPI strip, in-transit arrows, alert feed) and a
deep-dive per tier (**Provider / Manufacturer / Retailer**) with stock-vs-capacity
bars, order lists, and trend charts. The page auto-refreshes and degrades
gracefully when a service or the simulation isn't running yet.

> The dashboard uses **no authentication**. The provider and retailer are read
> from their public endpoints; the manufacturer's inventory/orders endpoints
> require a login, so the manufacturer tile is instead populated from its
> (no-auth) per-day `metrics` table — finished stock, raw parts, production
> utilisation, and sales-order counts. That data appears once a run starts
> writing metrics (it is empty at day 0).

Frontend assets (HTML/CSS/JS) live in `frontend/`; the FastAPI app and data
collectors live in the `dashboard/` package. Run its tests with:

```bash
PYTHONPATH=. ./manufacturer/venv/bin/pytest dashboard/tests/ -v
```

### 6. Running Tests

Run the focused delivery-sync regression tests before any full scenario run:

```bash
cd manufacturer && pytest tests/test_api/test_day_advance.py -W error
cd ../retailer && pytest tests/test_services/test_purchase_order_sync.py
```

Run all project-level integration and logic tests:

```bash
# Uses manufacturer venv for dependencies
export PYTHONPATH=$PYTHONPATH:.
./manufacturer/venv/bin/pytest tests/
```

### 7. Stop all services

```bash
pkill -f 'cli serve'
```

---

## Project Structure

```
week-08/
├── provider/          # Parts supplier service (:8001)
├── manufacturer/      # Printer factory service (:8002)
├── retailer/          # Retail store service (:8003)
├── turn_engine.py     # Orchestrates agents through simulated time
├── visualize.py       # Generates analysis charts from metrics DBs
├── config/sim.json    # Agent wiring (skill files, service URLs)
├── scenarios/         # Scenario JSON files
├── skills/            # LLM agent skill files (one per role)
├── scripts/           # Setup, start, reset helpers
├── logs/              # Per-turn agent logs, run.csv, and charts/ (git-ignored)
└── docs/
    ├── PRD.md         # Full product spec
    ├── PLAN.md        # Implementation task list
    └── ANALYSIS.md    # Visualization requirements and interpretation guide
```

---

## Scenarios

| File | Days | Description |
|---|---|---|
| `scenarios/calm-market.json` | 15 | Steady baseline, no disruptions |
| `scenarios/holiday-rush.json` | 25 | Black Friday + chip shortage + Christmas rush |

---

## Docs

- **`docs/PRD.md`** — full system spec, scenario format, metrics schema, analysis requirements
- **`docs/PLAN.md`** — current state, task list, verification checklist
