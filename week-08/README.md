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

After a simulation run, generate charts to analyze agent behavior and supply chain dynamics. You can visualize the "live" current state or an archived run:

```bash
# Visualize the most recent "live" run
./manufacturer/venv/bin/python visualize.py

# Visualize a specific archived scenario
./manufacturer/venv/bin/python visualize.py logs/calm-market
./manufacturer/venv/bin/python visualize.py logs/holiday-rush
```

Charts are saved to `logs/charts/{scenario_name}/` (or a `charts/` subdirectory of the archive folder if provided).

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
