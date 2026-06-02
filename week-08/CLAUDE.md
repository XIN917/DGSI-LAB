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
├── dashboard.py       # Dashboard entry point (venv/bin/python dashboard.py → :8080)
├── dashboard/         # Dashboard app package
├── frontend/          # Dashboard static files (HTML/JS/CSS)
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

Each service has its own virtualenv at `<service>/venv/`. A root-level `venv/` (created by `scripts/setup_envs.sh`) owns the orchestration layer: `turn_engine.py`, `api_server.py`, `visualize.py`, and `tests/`.

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

Generates 6 charts per scenario to analyze supply chain performance.
```bash
# Generate charts for all products/parts across all recent runs in logs/run.csv
python3 visualize.py

# Generate charts for a specific archived folder (even if run.csv is missing)
python3 visualize.py logs/calm-market
```

**Output files (all in `logs/{scenario}/charts/`):**

| File | Content |
|---|---|
| `provider_stock.png` | Raw materials stock — small multiples per part |
| `provider_prices.png` | Part prices (tier-1) — small multiples per part |
| `manufacturer_stock.png` | Finished goods inventory per model |
| `manufacturer_prices.png` | Wholesale prices per model |
| `manufacturer_utilisation.png` | Production utilisation % per model |
| `retailer_stock.png` | Retail inventory per SKU |
| `retailer_prices.png` | Retail prices per SKU |
| `retailer_fulfillment.png` | Daily orders: fulfilled / backordered / lost |
| `scenario_events.png` | Demand / supply / lead-time multipliers over time |

**Features:**
- **Per-service grouping**: Charts are separated by service (Provider / Manufacturer / Retailer) matching the dashboard layout.
- **Event shading**: All charts show colored bands for scenario events (Black Friday = blue, Chip Shortage = orange, Christmas Rush = purple).
- **Small multiples**: Provider stock and prices use a per-part grid.
- **Seed-price filter**: Day-1 manufacturer price anomalies (> 3× median) are suppressed automatically.
- **Resilience**: Stock/Price charts generate from SQLite databases even if `run.csv` is missing.

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
provider-cli price set <product_id> <min_quantity> <unit_price>
provider-cli seed          # initialise DB
provider-cli serve --port 8001
```

### Manufacturer (:8002) — `manufacturer/venv/bin/manufacturer-cli`
```
manufacturer-cli day current
manufacturer-cli stock
manufacturer-cli sales orders
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
9. Appends KPI row to `logs/{scenario}/run.csv` (file is cleared at the start of each fresh run of that scenario; resumed chunk runs preserve existing rows)
10. At end of run: snapshots databases to `logs/{scenario}/` and prints summary table including duration, model, and day range

**Optimizations:**
- **Full Parallelization**: All three agents run concurrently each day. Manufacturer operates on previous day's retailer orders (realistic 1-day lag).
- **Compact Role Contracts**: Normal runs send compact per-role rules instead of the full markdown skill files every day. Use `--full-skill-prompt` when debugging agent behavior against the original skill text.
- **Trimmed Prefetch**: Each agent receives decision-relevant state with long CLI outputs capped to preserve headers, active rows, and recent rows.
- **Action Batching**: Agents are instructed to use the prefetched state as their assessment step, avoid duplicate read-only commands, batch related mutations into as few Bash turns as practical, and keep final summaries under 120 words.
- **Model Flexibility**: Use `--model` to switch LLM brains. Claude models use the `claude` CLI subprocess; Gemini and Gemma models (`gemini-*`, `gemma-*`) use the `google-genai` SDK directly with `GEMINI_API_KEY` from `.env`. Default: `gemini-3.1-flash-lite`. Supported: `gemini-3.1-flash-lite`, `gemma-4-26b-a4b-it`, `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`, `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`, `claude-opus-4-7`.
- **Run Chunking**: Use `--start-day N` to resume long scenarios without rerunning previous days.
- **Auto Chart Generation**: At the end of every run, databases are snapshotted and `generate_charts()` from `visualize.py` is called automatically. Charts land in `logs/{scenario}/charts/`. Requires `matplotlib` and `pandas` in the environment; degrades gracefully if unavailable.

All scenario signal fields are parsed (`demand_modifier`, `supply_modifier`, `lead_time_modifier`, `price_sensitivity`). Overlapping events multiply modifiers.

Agent turn limits: retailer 6, manufacturer 8, provider 8. Per-agent wall-clock timeout: 300s (5 minutes) — if an agent exceeds this it is killed and the day continues without its output. **Do not reduce these max-turn budgets again**: provider and manufacturer hit `Reached max turns` during longer 25-day runs when the limits were lower, especially after day 10 when release failures and purchase orders require extra tool turns. The retailer budget was raised to 6 and provider/manufacturer to 8 after day-9 truncation in calm-market runs and to keep 25-day scenarios from stalling. Default output is compact; pass `-v` for full console display and `--full-skill-prompt` for full skill markdown prompts.

**Known gotcha:** `manufacturer/providers.json` must exist and point to the provider service URL. It is tracked in git. All databases are named consistently as `<service>.db` (e.g., `manufacturer/data/manufacturer.db`).

**Delivery sync invariant:** The turn engine advances services through HTTP, not the CLIs. Therefore all day-advance side effects required by a run must live in the HTTP advance paths too. Manufacturer `POST /api/day/advance` and `POST /api/simulation/advance` must poll external suppliers before advancing, and retailer purchase-order sync must keep checking every non-terminal PO until it is delivered or cancelled.

---

## Key Constraints

- **Never call `day advance` directly.** The turn engine does that via `POST /api/day/advance`.
- **Never change skill files to match the CLI.** The skill files are spec; fix the CLI.
- **Do not reduce agent max-turn budgets below retailer 6, manufacturer 8, provider 8.** These are intentionally higher than the first optimized values to keep long scenario runs from truncating valid decisions.
- **Keep compact prompts as the default for long runs.** Full skill prompts are for debugging; they increase token usage substantially over 25-day scenarios.
- **Overlapping scenario events multiply modifiers** (not last-wins). This is intentional — it produces the bullwhip effect.
- Price floors: P3D-Classic €163, P3D-Pro €246 (manufacturer minimum). Wholesale seed: €195 / €290. Retail seed: €295 / €435.
- One simulation run should complete in ≤ 30 minutes wall clock.

---

## Active "Do Not Revert" Constraints

These were fixed bugs with non-obvious resolutions — do not undo them:

- **`reload=False` in all services** — `reload=True` caused WatchFiles to restart the server mid-run on any file edit. Do not revert.
- **`markup=False` must NOT be set on the callback Console in `turn_engine.py`** — it causes `[bold]`, `[cyan]` etc. to render as raw text instead of ANSI codes. xterm.js needs the codes.
- **Agent max-turn budgets: retailer 6, manufacturer 8, provider 8** — lower budgets caused `Reached max turns` truncation in 25-day runs. Do not reduce.
- **`frame_kit` seed is 20, `frame_kit_pro` is 15** in `manufacturer/sample_data/default_production_plan.json` — intentionally low so the agent is forced to reorder within the first few days. Do not raise.
- **`start_new_session=True` in `scripts/start_all.sh`** — services must survive api_server restarts. `nohup`/`setsid` are insufficient.
- **Scenario log archives (`logs/{scenario}/`) are NOT deleted on reset** — only live DBs are cleared. Stale day logs are cleared per-scenario at run start in `turn_engine.py`.

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
| `scenarios/smoke-test.json` | 6 | Demo scenario: 3 normal days + 3-day flash sale (demand ×2.5) |

Days 18–20 in `holiday-rush` have two overlapping events — modifiers multiply.

---

## What Still Needs Doing

See `docs/PLAN.md` for the full ordered task list. Current status:

- Phase 1 (wiring + fixes) — **complete**
- Phase 2 (metrics tables) — **complete**
- Phase 3 (testing & visualization) — **complete**
- Phase 4 (analysis) — **complete** (both scenarios run and archived; all charts generated; ANALYSIS.md complete)
- Phase 5 (final deliverables) — not started (full end-to-end test run pending; Final Report PDF pending)

## Frontend API Server (`api_server.py`)

A FastAPI wrapper around `turn_engine.py` that exposes all simulation functionality over HTTP for frontend integration. Start it with:

```bash
pip install fastapi uvicorn
python api_server.py          # listens on :8000
# or: uvicorn api_server:app --reload --port 8000
```

Interactive docs at `http://localhost:8000/docs`.

**15 endpoints across 5 groups:**

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
- Run registry is **session-scoped** — only completed runs (done/cancelled/error) are persisted to `logs/runs.json` with their `elapsed_seconds`. No stale "running" entries survive a server restart.

**Next step for frontend integration:**
- The frontend teammate should connect to `POST /run` to start, then `GET /run/{id}/stream` for live log lines (SSE), and `GET /run/{id}/kpis` + `/charts` once the run finishes.
- CORS is open (`allow_origins=["*"]`) — restrict in production.

Also exposes two reset endpoints:
- `POST /reset` — fires `scripts/reset_all.sh` in a background thread; returns immediately
- `GET /reset/status` — returns `{status: "idle"|"running"|"done"|"error", output: "..."}`

## Live Dashboard (`dashboard/`)

A browser-based monitoring dashboard that proxies data from `api_server.py` and the three services.

See **`README.md`** for startup instructions. Open http://localhost:8080. Five pages:
- **Overview** — prominent day counter, color-coded KPI tiles (fill rate, backlog, prod util, active demand/supply modifiers), alerts strip, pipeline flow diagram, per-service live SVG charts
- **Provider / Manufacturer / Retailer** — per-service detail with inventory, prices, and orders
- **Simulation** — start/stop runs, pick scenario and model, stream live ANSI terminal output, reset to Day 0

**Design notes:**
- `dashboard/app.py` proxies all `/api/sim/*` calls to `api_server.py` (:8000) and exposes `/api/state` from the service DBs directly
- SVG charts are drawn client-side in `frontend/dashboard.js` using `d3`-style scaling; no PNG charts are fetched for the live view
- **Fill rate KPI** shows `total fulfilled / total orders` across all days in `run.csv` (matches summary.log). At day 0, fill rate, backlog, events, day_total, and fill_rate_series are all suppressed to avoid showing stale CSV data.
- **Backlog KPI** shows cumulative backordered orders summed from `run.csv`, not the current DB state (which resolves to 0 at end of run). Live path falls back to current order count when no CSV exists.
- **Provider in-transit** counts only `SHIPPED` orders (physically moving). `CONFIRMED` and `InProgress` are still at the provider being prepared.
- **Overview tier cards**: provider shows 3 lowest-stock parts; manufacturer shows only finished goods (parts hidden); sparklines match exactly the items shown. Price drift (↑/↓) shown per item.
- **Sparkline labels** shown below each overview sparkline when multiple series are present.
- **Event strip** shown above the header — all non-normal scenario events as chips with name, day range, demand mod, supply mod (supply in red when < 1). Sourced from `event_summary` in `/api/state` and `/api/archive/{scenario}/state`, built from the scenario JSON in `context.py`.
- **Order panels** on all service pages show a status summary bar (counts by status) above a scrollable list (newest first, LIMIT 500). Manufacturer orders come from `GET /api/orders` (no auth on any manufacturer endpoint). Provider and retailer orders sorted DESC in collector.py. Status colors: confirmed (cyan), in progress (purple), waiting materials (orange).
- **Manufacturer stock and orders**: `collector.py` calls `/api/inventory` and `/api/orders` directly (same as Provider/Retailer). Utilisation % still comes from the `metrics` table (the only source for it). Parts stock falls back to the `inventory` table at day 0 when the metrics table is empty.
- **Archive view**: a VIEW dropdown in the nav switches between live service data and any completed scenario archive. Selecting a scenario loads `logs/{scenario}/*.db` and `logs/{scenario}/run.csv` via `GET /api/archive/{scenario}/state`. Selection persists across pages via `sessionStorage`. Archives survive resets.
- **Simulation page selections** (scenario, model, days, start day) persist across page navigation via `sessionStorage`.
- Reset is fire-and-forget: `POST /api/sim/reset` returns immediately; frontend polls `GET /api/sim/reset/status` every 2 s; on page re-init the polling resumes if status is `"running"`
- Terminal output is rendered by xterm.js — ANSI codes from Rich are rendered natively; `markup=False` must NOT be set on the callback Console in `turn_engine.py`. Rich console width is set to 150 to fit the terminal area.
- Services launched by `scripts/start_all.sh` use `start_new_session=True` so they stay running when `api_server.py` restarts
- Customer orders panel has a scrollable list (max 280px); shows up to 500 orders; scroll position is preserved across 2 s refreshes
- Simulation page log dropdown auto-selects the first scenario that has logs; log/summary content panels restore `display:block` on click
- Run chips show day range (`d1–10`) and elapsed time in seconds (`4m 42s`); duration is frozen at completion and does not grow after the run ends
- Scenario log archives (`logs/{scenario}/`) survive reset — only the live DBs are cleared. Per-scenario `run.csv` files are cleared at the start of each new run of that scenario.

## Cheap Verification Before Full Runs

Full 15/25-day agent simulations are slow and token-expensive. Before rerunning scenarios, verify the delivery-sync path with focused tests:

```bash
manufacturer/venv/bin/pytest manufacturer/tests/test_api/test_day_advance.py -W error
retailer/venv/bin/pytest retailer/tests/test_services/test_purchase_order_sync.py
```

Only after these pass should you spend tokens on a scenario run. For a low-cost end-to-end smoke check, reset and run 3-5 calm-market days, then inspect archived SQLite databases for manufacturer supplier POs moving to `delivered` with `quantity_delivered > 0`, and retailer POs moving to `delivered` with `received_day` populated.
