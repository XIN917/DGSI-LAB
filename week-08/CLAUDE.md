# CLAUDE.md — DGSI Week 8: Supply Chain Simulation

## What This Project Is

An autonomous multi-agent supply chain simulation. Three services (Provider, Manufacturer, Retailer) each run by an LLM agent. A turn engine orchestrates them through simulated days. Scenarios inject market pressure. The goal is emergent coordination — agents share no memory and never talk directly; the only shared state is the world in their databases.

Full spec: `docs/PRD.md` | Tasks: `docs/PLAN.md` | Requirements: `docs/REQUIREMENTS.md`

---

## Project Structure

```
week-08/
├── provider/          # Parts supplier service (:8001)
├── manufacturer/      # Printer factory service (:8002)
├── retailer/          # Retail store service (:8003)
├── turn_engine.py     # Orchestrates all three agents per simulated day
├── api_server.py      # FastAPI wrapper for frontend integration (:8000)
├── config/sim.json    # Agent wiring (skill files, URLs, paths)
├── scenarios/         # Scenario JSON files (calm-market, holiday-rush)
├── skills/            # Agent skill files (one per role)
├── scripts/           # Setup, start, reset scripts
├── logs/              # Per-turn agent logs and generated charts (git-ignored)
├── tests/             # Project-level integration and logic tests
└── docs/
    ├── PRD.md         # Product spec
    ├── PLAN.md        # Task list and current state
    ├── REQUIREMENTS.md # Consolidated project requirements
    ├── ANALYSIS.md     # Visualization and interpretation guide
    └── DELIVERY.md     # Final submission checklist
```

Each service has its own virtualenv at `<service>/venv/`.

---

## How to Run & Test
See **`README.md`** for detailed instructions on:
- Setting up environments
- Starting/Stopping services
- Running simulations (`turn_engine.py`)
- Generating charts (`visualize.py`)
- Running project-level tests (`pytest tests/`)

---

## Visualization (`visualize.py`)

Generates 4 charts per scenario to analyze supply chain performance.
```bash
# Generate charts for all products/parts across all recent runs in logs/run.csv
python3 visualize.py

# Generate charts for a specific archived folder (even if run.csv is missing)
python3 visualize.py demo/calm-market_1
```
**Features:**
- **Split Subplots**: Inventory and Price charts are split into "Finished Goods" and "Raw Materials" panels to handle different scales.
- **Multi-Product**: Automatically loops through all models (Classic, Pro) and all 11 raw parts.
- **Resilience**: Generates Inventory/Price charts from SQLite databases even if the `run.csv` summary is missing.

---

## Services and CLIs
...
### Provider (:8001) — `provider/venv/bin/provider-cli`
```
provider-cli day current
provider-cli catalog
provider-cli stock
provider-cli orders list [--status pending]
provider-cli orders show <id>
provider-cli restock <product> <quantity>
provider-cli price set <product> <tier> <price>
provider-cli seed          # initialise DB
provider-cli serve --port 8001
```

### Manufacturer (:8002) — `manufacturer/venv/bin/manufacturer-cli`
```
manufacturer-cli day current
manufacturer-cli stock
manufacturer-cli sales orders / sales order <id>
manufacturer-cli production status / production release <order_id>
manufacturer-cli capacity
manufacturer-cli suppliers list / suppliers catalog <name>
manufacturer-cli purchase list / purchase create --supplier <name> --product <id> --qty <n>
manufacturer-cli price list / price set <model> <price>
manufacturer-cli seed
manufacturer-cli serve --port 8002
```

### Retailer (:8003) — `retailer/venv/bin/retailer-cli`
```
retailer-cli day current
retailer-cli stock                              # skill-aligned (also: inventory)
retailer-cli customers orders                   # skill-aligned (also: customer-orders list)
retailer-cli customers order <id>
retailer-cli fulfill <order_id>
retailer-cli backorder <order_id>
retailer-cli purchase list                      # skill-aligned (also: purchase-orders list)
retailer-cli purchase create <model> <qty>      # skill-aligned
retailer-cli price list                         # skill-aligned
retailer-cli price set <model> <price>          # skill-aligned
retailer-cli init
retailer-cli serve --port 8003
```

---

## Agent Skill Files

Skill files live in `skills/`. They define each agent's role, available commands, constraints, and decision framework. **They are authoritative from `week8.pdf` — do not change them to match the CLI. Change the CLI to match them.**

- `skills/provider-manager.md` — wired in `config/sim.json`
- `skills/manufacturer-manager.md` — wired in `config/sim.json`
- `skills/retail-manager.md` — wired in `config/sim.json`

---

## Turn Engine

`turn_engine.py` drives the simulation. Each day:
1. Reads scenario signal for the day (`todays_signal()`)
2. Generates customer demand at retailer
3. On Day 1 only: seeds random purchase orders (Classic + Pro) at the retailer so the manufacturer has something to process from the start
4. Prefetches state for all agents (Retailer, Manufacturer, Provider) in parallel
5. Runs all three agents in parallel (manufacturer processes previous day's retailer orders)
6. Calls `POST /api/day/advance` on each service
7. Saves all three agents' output to `logs/{scenario}/day-NNN.log`
8. Prints global inventory snapshot table (all three services)
9. Appends KPI row to `logs/run.csv`
10. At end of run: snapshots databases to `logs/{scenario}/` and prints summary table

**Optimizations:**
- **Full Parallelization**: All three agents run concurrently each day. Manufacturer operates on previous day's retailer orders (realistic 1-day lag).
- **Compact Role Contracts**: Normal runs send compact per-role rules instead of the full markdown skill files every day. Use `--full-skill-prompt` when debugging agent behavior against the original skill text.
- **Trimmed Prefetch**: Each agent receives decision-relevant state with long CLI outputs capped to preserve headers, active rows, and recent rows.
- **Action Batching**: Agents are instructed to use the prefetched state as their assessment step, avoid duplicate read-only commands, batch related mutations into as few Bash turns as practical, and keep final summaries under 120 words.
- **Model Flexibility**: Use `--model` to switch LLM brains. Claude models use the `claude` CLI subprocess; Gemini models (`gemini-*`) use the `google-genai` SDK directly with `GEMINI_API_KEY` from `.env`. Supported: `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`, `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`.
- **Run Chunking**: Use `--start-day N` to resume long scenarios without rerunning previous days.
- **Auto Chart Generation**: At the end of every run, databases are snapshotted and `generate_charts()` from `visualize.py` is called automatically. Charts land in `logs/{scenario}/charts/`. Requires `matplotlib` and `pandas` in the environment; degrades gracefully if unavailable.

All scenario signal fields are parsed (`demand_modifier`, `supply_modifier`, `lead_time_modifier`, `price_sensitivity`). Overlapping events multiply modifiers.

Agent turn limits: retailer 6, manufacturer 8, provider 8. **Do not reduce these max-turn budgets again**: provider and manufacturer hit `Reached max turns` during longer 25-day runs when the limits were lower, especially after day 10 when release failures and purchase orders require extra tool turns. The retailer budget was raised to 6 and provider/manufacturer to 8 after day-9 truncation in calm-market runs and to keep 25-day scenarios from stalling. Default output is compact; pass `-v` for full console display and `--full-skill-prompt` for full skill markdown prompts.

**Known gotcha:** `manufacturer/providers.json` must exist and point to the provider service URL. It is tracked in git. All databases are named consistently as `<service>.db` (e.g., `manufacturer/data/manufacturer.db`).

**Delivery sync invariant:** The turn engine advances services through HTTP, not the CLIs. Therefore all day-advance side effects required by a run must live in the HTTP advance paths too. Manufacturer `POST /api/day/advance` and authenticated `POST /api/simulation/advance` must poll external suppliers before advancing, and retailer purchase-order sync must keep checking every non-terminal PO until it is delivered or cancelled.

---

## Key Constraints

- **Never call `day advance` directly.** The turn engine does that via `POST /api/day/advance`.
- **Never change skill files to match the CLI.** The skill files are spec; fix the CLI.
- **Do not reduce agent max-turn budgets below retailer 6, manufacturer 8, provider 8.** These are intentionally higher than the first optimized values to keep long scenario runs from truncating valid decisions.
- **Keep compact prompts as the default for long runs.** Full skill prompts are for debugging; they increase token usage substantially over 25-day scenarios.
- **Overlapping scenario events multiply modifiers** (not last-wins). This is intentional — it produces the bullwhip effect.
- Price floors: P3D-Classic €163, P3D-Pro €246 (manufacturer minimum).
- One simulation run should complete in ≤ 30 minutes wall clock.

---

## Known Bugs Fixed

- **`reload=True` uvicorn bug:** All three services had `reload=True` which caused WatchFiles to restart the server mid-run when any file was edited. Fixed to `reload=False` in all three `cli.py` serve commands. Do not revert this.
- **Agent max-turns bug:** Prompts previously asked agents to `Read <skill_file>` which consumed a turn before any action. Fixed by embedding skill content directly in the prompt string in `turn_engine.py`.
- **Long-run max-turn truncation:** Provider/manufacturer later hit `Reached max turns` in 25-day runs after earlier turn limits were set too low. Current budgets are retailer 6, manufacturer 8, provider 8; keep them there unless a future change proves a higher budget is needed.
- **Manufacturer never orders frame_kit:** Seed was 120 units — enough for 30+ days of calm demand, so the agent never triggered a reorder. Lowered to 20 (frame_kit) and 15 (frame_kit_pro) in `manufacturer/sample_data/default_production_plan.json` so the agent must order within the first few days.
- **prices.png zigzag:** Manufacturer metrics table writes multiple rows per sim_day (one per price change). Fixed in `visualize.py` with `groupby(...).last()` deduplication.
- **HTTP advance skipped external supplier receipts:** Manufacturer CLI `day advance` polled external suppliers, but the turn engine uses HTTP `POST /api/day/advance`, so provider deliveries reduced provider stock while manufacturer raw-material inventory stayed frozen. Fixed by polling `ExternalSupplierService` in both manufacturer HTTP advance endpoints.
- **Retailer stranded in-flight manufacturer POs:** Retailer delivery sync only checked local POs with status `pending`; once a PO became `released` or `waiting_materials`, later manufacturer delivery was never received into retailer stock. Fixed by syncing all non-terminal POs (`not delivered/cancelled`).
- **Python/Pydantic warnings in regression tests:** Updated manufacturer settings to Pydantic v2 `SettingsConfigDict`, replaced `datetime.utcnow()` with timezone-aware `datetime.now(UTC)`, and disposed the SQLite test engine.

---

## Simulation Philosophy (From Week8.pdf)

**The goal is not a clean run. The goal is a readable run.**

What Can Go Wrong (and what to do about it):
- **Agent mistakes:** An agent making a bad call and cascading into a crisis. **Do not rewind** — watch what happens.
- **Ambiguities:** A skill ambiguity revealing itself mid-run. Note it, let the run finish, and fix the skill for the next run.
- **Timeouts:** Stuck agents (timeouts). Log them, move on. A system that survives one flaky agent is more interesting than a perfect one.

---

## Scenarios

| File | Days | Description |
|---|---|---|
| `scenarios/calm-market.json` | 15 | Steady baseline, no disruptions |
| `scenarios/holiday-rush.json` | 25 | Black Friday (11–13) + chip shortage (14–20) + Christmas (18–25) |

Days 18–20 in `holiday-rush` have two overlapping events — modifiers multiply.

---

## What Still Needs Doing

See `docs/PLAN.md` for the full ordered task list. Current status:

- Phase 1 (wiring + fixes) — **complete**
- Phase 2 (metrics tables) — **complete**
- Phase 3 (testing & visualization) — **complete** (visualize.py implemented and integrated into turn_engine.py; charts auto-generated at end of each run to `logs/{scenario}/charts/`; 15-day calm-market verified)
- Phase 4 (analysis) — **in progress** (holiday-rush 25-day run pending; calm-market charts done)
- Phase 5 (final deliverables) — not started

## Frontend API Server (`api_server.py`)

A FastAPI wrapper around `turn_engine.py` that exposes all simulation functionality over HTTP for frontend integration. Start it with:

```bash
pip install fastapi uvicorn
python api_server.py          # listens on :8000
# or: uvicorn api_server:app --reload --port 8000
```

Interactive docs at `http://localhost:8000/docs`.

**16 endpoints across 5 groups:**

| Group | Endpoints |
|---|---|
| Simulation control | `POST /run`, `DELETE /run/{id}`, `GET /run/{id}/stream` (SSE), `GET /run/{id}/status`, `GET /runs` |
| Scenario/config | `GET /scenarios`, `GET /scenarios/{name}`, `GET /models` |
| Run data | `GET /run/{id}/logs` (paginated), `GET /run/{id}/kpis`, `GET /run/{id}/inventory`, `GET /run/{id}/prices` |
| Charts | `GET /run/{id}/charts`, `GET /run/{id}/charts/{filename}` |
| Services | `GET /services/status` |

**Key design:**
- `POST /run` returns a `run_id` immediately; simulation runs in a background thread
- `GET /run/{id}/stream` is an SSE endpoint — connect with `EventSource` in the frontend
- `GET /run/{id}/inventory` and `/prices` query archived SQLite snapshots (populated at end of run)
- `DELETE /run/{id}` is best-effort cancel (stops after current day completes)
- `turn_engine.run_simulation()` accepts a `progress_cb` callback so the API server and CLI both work without code duplication

**Next step for frontend integration:**
- The frontend teammate should connect to `POST /run` to start, then `GET /run/{id}/stream` for live log lines (SSE), and `GET /run/{id}/kpis` + `/charts` once the run finishes.
- CORS is open (`allow_origins=["*"]`) — restrict in production.

## Cheap Verification Before Full Runs

Full 15/25-day agent simulations are slow and token-expensive. Before rerunning scenarios, verify the delivery-sync path with focused tests:

```bash
cd manufacturer
pytest tests/test_api/test_day_advance.py -W error

cd ../retailer
pytest tests/test_services/test_purchase_order_sync.py
```

Only after these pass should you spend tokens on a scenario run. For a low-cost end-to-end smoke check, reset and run 3-5 calm-market days, then inspect archived SQLite databases for manufacturer supplier POs moving to `delivered` with `quantity_delivered > 0`, and retailer POs moving to `delivered` with `received_day` populated.
