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

# Full agent reasoning output (default: compact 3-line summary)
python turn_engine.py config/sim.json scenarios/calm-market.json 15 -v
```

Agent logs are saved to `logs/day-NNN-[role].log` after each turn. KPI data (fulfillment rate, demand/supply modifiers) is appended to `logs/run.csv` for analysis.

> **Note:** `manufacturer/providers.json` must exist and point to the provider URL (`http://127.0.0.1:8001`). It is tracked in git — if missing, manufacturer procurement will silently fail every day.

### 5. Visualize Results

After a simulation run, generate charts to analyze agent behavior and supply chain dynamics:

```bash
# Uses manufacturer venv which has matplotlib/pandas installed
./manufacturer/venv/bin/python visualize.py
```

Charts are saved to `docs/charts/{scenario_name}/`.

### 6. Running Tests

Run the project-level integration and logic tests to verify the system:

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
├── logs/              # Per-turn agent logs and run.csv (git-ignored)
└── docs/
    ├── PRD.md         # Full product spec
    ├── PLAN.md        # Implementation task list
    ├── ANALYSIS.md    # Visualization requirements and interpretation guide
    └── charts/        # Generated analysis plots (git-ignored)
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
