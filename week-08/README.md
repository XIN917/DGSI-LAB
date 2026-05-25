# DGSI Supply Chain Ecosystem (Week 8)

A multi-service supply chain simulator consisting of a parts **Provider**, a 3D printer **Manufacturer**, and a downstream **Retailer**. Week 8 adds scenario-driven autonomous turns, role skills, daily metrics snapshots, and chart generation.

## Project Structure

- **[Provider](./provider/README.md)**: Simulates a raw materials supplier (PCBs, Motors, etc.) with a REST API.
- **[Manufacturer](./manufacturer/README.md)**: Simulates a 3D printer factory. Manages BOMs, production lines, and wholesale fulfillment.
- **[Retailer](./retailer/README.md)**: Simulates a consumer store. Manages retail pricing, customer demand, and stock replenishment.

## Configuration & Security

The Manufacturer service refuses to boot without a non-empty `SECRET_KEY`
(JWT signing key). Create `manufacturer/.env` from `manufacturer/.env.example`:

```bash
cp manufacturer/.env.example manufacturer/.env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"  # paste into SECRET_KEY=
```

> ⚠️ **Secrets policy** — Never commit `.env`, API keys, or tokens. If a
> credential is ever pushed (even briefly), rotate it on the provider's
> console immediately; removing it from the working tree does NOT remove
> it from git history. `.gitignore` already excludes `.env`, `*.db`, and
> `logs/`.

## Quick Start (Installation)

To get started, you must set up the virtual environment for each service. From the root directory:

```bash
# Setup Provider
cd provider && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt && ./venv/bin/pip install -e . && cd ..

# Setup Manufacturer
cd manufacturer && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt && ./venv/bin/pip install -e . && cd ..

# Setup Retailer
cd retailer && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt && ./venv/bin/pip install -e . && cd ..
```

## 🚀 Automated Simulation

The full supply chain lifecycle can be executed using the provided automation scripts:

1.  **Start all servers:**
    ```bash
    ./scripts/start_all.sh
    ```
2.  **Run the core simulation scenario:**
    ```bash
    ./scripts/test_scenario.sh
    ```
    *This script handles database seeding, demand generation, production release, and time advancement automatically.*

## Week 8 Autonomous Runs

Start from clean state, run a scenario, and generate charts:

```bash
./scripts/run_week8.sh scenarios/holiday-rush.json 25
```

The direct engine command is:

```bash
manufacturer/venv/bin/python turn_engine.py config/sim.json scenarios/holiday-rush.json 25
```

For deterministic fallback-only smoke runs:

```bash
WEEK8_CONFIG=config/sim-fallback.json ./scripts/run_week8.sh scenarios/calm-market.json 1
```

For a one-day demo after services are running:

```bash
./scripts/reset_simulation.sh
./scripts/start_all.sh
manufacturer/venv/bin/python turn_engine.py config/sim.json scenarios/calm-market.json 1
manufacturer/venv/bin/python analysis/generate_charts.py scenarios/calm-market.json
```

Generated role logs are written to `logs/day-XXX-role.log`. Metrics snapshots are persisted in each service SQLite database and charts are written under `analysis/output/<scenario>/`.

Claude agents are attempted through `/Users/david.morais/.local/bin/claude` when available. If Claude is missing, times out, or returns an error, deterministic fallback decisions keep the simulation moving.

Project scripts source `scripts/use_pypi.sh`, which temporarily sets `PIP_INDEX_URL=https://pypi.org/simple` for this project only.

## Week 8 Files

- `turn_engine.py`: REST-based day engine.
- `scenario_utils.py`: scenario signal merging and deterministic demand.
- `config/sim.json`: service URLs, Claude timeout, demand parameters, and fallback thresholds.
- `config/sim-fallback.json`: same run settings with Claude disabled for deterministic testing.
- `scenarios/calm-market.json`, `scenarios/holiday-rush.json`: reproducible scenario definitions.
- `skills/*.md`: role instructions for Retailer, Manufacturer, and Provider agents.
- `analysis/generate_charts.py`: metrics chart generation.

## 🛠 Manual Simulation

For a detailed step-by-step guide on how to run a manual, day-by-day simulation and monitor logs across separate terminal windows, see the **[Testing & Integration Guide](./docs/TESTING.md)**.

## Integration Progress

Track the Week 7 development and integration status in:
- **[Integration Plan](./docs/retailer_integration_plan.md)**
- **[Integration Log](./docs/INTEGRATION.md)**
