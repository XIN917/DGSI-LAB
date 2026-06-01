# DGSI Week 8 — Supply Chain Simulation

Autonomous multi-agent supply chain for 3D printers. Three services (Provider, Manufacturer, Retailer) each driven by an LLM agent. A turn engine orchestrates them through simulated days. Scenarios inject market pressure.

---

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

---

## Quickstart

### 0. Set up API key

The default agent model is `gemini-3.1-flash-lite`. Create a `.env` file at the repo root with your Gemini API key:

```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

Get a key at https://aistudio.google.com/apikey. The `.env` file is git-ignored.

Supported models: `gemini-3.1-flash-lite` (default), `gemma-4-26b`, `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash` (all via `GEMINI_API_KEY`), and `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`, `claude-opus-4-7` (require the `claude` CLI).

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

Agent logs are saved to `logs/{scenario_name}/day-NNN.log`. Databases are snapshotted and charts are automatically generated to `logs/{scenario_name}/` at the end of each run. KPI data is written to `logs/{scenario_name}/run.csv` (one file per scenario, cleared at the start of each fresh run of that scenario). Normal runs use compact role contracts and capped prefetch output to reduce token usage; pass `--full-skill-prompt` only when debugging agent behavior.

> **Note:** `manufacturer/providers.json` must exist and point to the provider URL (`http://127.0.0.1:8001`). It is tracked in git — if missing, manufacturer procurement will silently fail every day.
>
> **Note:** All three services run with `reload=False`. Do not change this — `reload=True` causes WatchFiles to restart the server mid-run if any file is edited, corrupting the manufacturer DB mid-simulation.
>
> **Note:** Manufacturer seed inventory for `frame_kit` is intentionally low (20 units) so the manufacturer agent is forced to order from the provider within the first few days. Do not raise it or the reorder behavior disappears in short runs.

### 5. Visualize Results (manual / re-run)

Charts are generated automatically at the end of every simulation run. To regenerate them manually or for an archived folder:

```bash
# Regenerate charts from a specific archived folder
python visualize.py logs/holiday-rush
python visualize.py logs/calm-market

# Regenerate for the most recent run
python visualize.py
```

### 6. Running Tests

Run the focused delivery-sync regression tests before any full scenario run:

```bash
manufacturer/venv/bin/pytest manufacturer/tests/test_api/test_day_advance.py -W error
retailer/venv/bin/pytest retailer/tests/test_services/test_purchase_order_sync.py
```

Run all project-level tests (logic, API, and UI):

```bash
# Unit + API tests — no live services needed
venv/bin/pytest tests/test_simulation_logic.py tests/test_api_server.py -v

# UI tests — requires the full stack running (see step 7)
venv/bin/pytest tests/test_ui_dashboard.py -v --run-ui

# Everything at once
venv/bin/pytest tests/ -v --run-ui
```

**Test files in `tests/`:**

| File | What it covers | Needs live services? |
|---|---|---|
| `test_simulation_logic.py` | Turn engine helpers (signal parsing, compact output, role contracts) | No |
| `test_api_server.py` | All 15 `api_server.py` endpoints via FastAPI `TestClient` | No |
| `test_ui_dashboard.py` | 20 Playwright browser tests — nav, reset banner, simulation controls, archive view | Yes (`--run-ui`) |

The `--run-ui` flag enables UI tests. Without it they are silently skipped, so a plain `venv/bin/pytest tests/` always passes even without a running dashboard.

Each service also has its own tests:

```bash
manufacturer/venv/bin/pytest manufacturer/tests/ -v
retailer/venv/bin/pytest retailer/tests/ -v
provider/venv/bin/pytest provider/tests/ -v
```

### 7. Live Dashboard

A browser-based monitoring dashboard shows real-time inventory, prices, fulfillment, and service health — and lets you start/reset simulations from the UI.

```bash
# Start api_server first (if not already running)
venv/bin/python api_server.py          # :8000

# Then start the dashboard
venv/bin/python dashboard.py           # :8080
```

Open http://localhost:8080. The dashboard has five pages:
- **Overview** — prominent day counter, color-coded KPI tiles (avg fill rate, backlog, prod util, active demand/supply modifiers), alerts strip, pipeline flow diagram, per-service SVG charts; all KPIs suppressed at day 0 to avoid showing stale data
- **Provider / Manufacturer / Retailer** — per-service inventory, prices, and orders
- **Simulation** — start/stop runs, choose scenario and model, stream live terminal output, reset to Day 0

A **VIEW** dropdown in the nav bar lets you switch between the live service state and any completed scenario archive (`logs/{scenario}/`). Archives persist across resets so you can compare calm-market and holiday-rush side by side.

> **Note:** Services launched via `scripts/start_all.sh` use `start_new_session=True` so they stay up when `api_server.py` restarts.

### 8. Stop all services

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
├── api_server.py      # FastAPI wrapper for frontend integration (:8000)
├── visualize.py       # Generates analysis charts from metrics DBs
├── config/sim.json    # Agent wiring (skill files, service URLs)
├── scenarios/         # Scenario JSON files
├── skills/            # LLM agent skill files (one per role)
├── scripts/           # Setup, start, reset helpers
├── dashboard.py       # Dashboard entry point (:8080)
├── dashboard/         # Dashboard app package
├── frontend/          # Dashboard HTML/JS/CSS
├── logs/              # Per-turn agent logs and charts/ (git-ignored)
│   └── {scenario}/    # Per-scenario archive: day logs, run.csv, *.db snapshots, charts/
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
