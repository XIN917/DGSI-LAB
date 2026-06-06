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
├── dashboard.py       # Dashboard entry point (:8080)
├── dashboard/         # Dashboard app package
├── frontend/          # Dashboard static files (HTML/JS/CSS)
├── config/sim.json    # Agent wiring (skill files, URLs, paths)
├── scenarios/         # Scenario JSON files (calm-market, holiday-rush, smoke-test)
├── skills/            # Agent skill files (one per role)
├── scripts/           # Setup, start, stop, reset scripts
├── logs/              # Per-turn agent logs and generated charts (git-ignored)
├── tests/             # Project-level integration and logic tests
└── docs/
    ├── PRD.md         # Product spec
    ├── PLAN.md        # Task list and current state (single source of truth)
    ├── REQUIREMENTS.md # Requirements spec (no checkboxes)
    ├── ANALYSIS.md    # Visualization and interpretation guide
    └── DASHBOARD.md   # Dashboard design notes and implementation details
```

Each service has its own virtualenv at `<service>/venv/`. A root-level `venv/` (created by `scripts/setup_envs.sh`) owns the orchestration layer: `turn_engine.py`, `api_server.py`, `visualize.py`, and `tests/`.

---

## How to Run & Test

See **`README.md`** for detailed instructions on setting up, starting/stopping services, running simulations, and tests.

---

## Services and CLIs

### Provider (:8001) — `provider/venv/bin/provider-cli`
```
provider-cli day current
provider-cli catalog
provider-cli stock
provider-cli orders list [--status pending]
provider-cli orders show <id>
provider-cli restock <product> <quantity>
provider-cli price set <product_id> <min_quantity> <unit_price>
provider-cli seed
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
retailer-cli stock
retailer-cli customers orders
retailer-cli customers order <id>
retailer-cli fulfill <order_id>
retailer-cli backorder <order_id>
retailer-cli purchase list
retailer-cli purchase create <model> <qty>
retailer-cli price list / price set <model> <price>
retailer-cli init
retailer-cli serve --port 8003
```

---

## Agent Skill Files

Skill files live in `skills/`. They define each agent's role, available commands, constraints, and decision framework. **They are authoritative — do not change them to match the CLI. Change the CLI to match them.**

- `skills/provider-manager.md` — wired in `config/sim.json`
- `skills/manufacturer-manager.md` — wired in `config/sim.json`
- `skills/retail-manager.md` — wired in `config/sim.json`

---

## Turn Engine

`turn_engine.py` drives the simulation. Each day:
1. Reads scenario signal for the day (`todays_signal()`)
2. Generates customer demand at retailer
3. On Day 1 only: seeds random purchase orders (Classic + Pro) at the retailer
4. Prefetches state for all agents in parallel
5. Runs all three agents in parallel (manufacturer processes previous day's retailer orders)
6. Calls `POST /api/day/advance` on each service
7. Saves all three agents' output to `logs/{scenario}/day-NNN.log`
8. Prints global inventory snapshot table
9. Appends KPI row to `logs/{scenario}/run.csv`
10. At end of run: snapshots databases and generates charts to `logs/{scenario}/`

**Model flexibility:** Default `gemini-3.1-flash-lite`. Supported: `gemini-3.1-flash-lite`, `gemma-4-26b-a4b-it`, `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`, `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`, `claude-opus-4-7`.

Agent turn limits: retailer 6, manufacturer 8, provider 8. Per-agent timeout: 300s.

**Known gotcha:** `manufacturer/providers.json` must exist and point to the provider service URL. It is tracked in git.

**Delivery sync invariant:** The turn engine advances services through HTTP, not the CLIs. All day-advance side effects must live in the HTTP advance paths. Manufacturer `POST /api/day/advance` must poll external suppliers before advancing; retailer PO sync must check every non-terminal PO until delivered or cancelled.

---

## Key Constraints

- **Never call `day advance` directly.** The turn engine does that via `POST /api/day/advance`.
- **Never change skill files to match the CLI.** The skill files are spec; fix the CLI.
- **Do not reduce agent max-turn budgets below retailer 6, manufacturer 8, provider 8.**
- **Keep compact prompts as the default for long runs.** Use `--full-skill-prompt` only for debugging.
- **Overlapping scenario events multiply modifiers** (not last-wins).
- Price floors: P3D-Classic €163, P3D-Pro €246. Wholesale seed: €195 / €290. Retail seed: €295 / €435.

---

## Active "Do Not Revert" Constraints

- **`reload=False` in all services** — `reload=True` causes WatchFiles to restart mid-run.
- **`markup=False` must NOT be set on the callback Console in `turn_engine.py`** — breaks ANSI rendering in xterm.js.
- **Agent max-turn budgets: retailer 6, manufacturer 8, provider 8** — lower values caused truncation in 25-day runs.
- **`frame_kit` seed is 20, `frame_kit_pro` is 15** — intentionally low to force reordering. Do not raise.
- **`start_new_session=True` in `scripts/start_services.sh`** — services must survive api_server restarts.
- **Scenario log archives (`logs/{scenario}/`) are NOT deleted on reset** — only live DBs are cleared.

---

## Scenarios

| File | Days | Description |
|---|---|---|
| `scenarios/calm-market.json` | 15 | Steady baseline, no disruptions |
| `scenarios/holiday-rush.json` | 25 | Black Friday (11–13) + chip shortage (14–20) + Christmas (18–25) |
| `scenarios/smoke-test.json` | 6 | 3 normal days + 3-day flash sale (demand ×2.5) |

Days 18–20 in `holiday-rush` have two overlapping events — modifiers multiply.

---

## Simulation Philosophy (From Week8.pdf)

**The goal is not a clean run. The goal is a readable run.**

- **Agent mistakes:** Do not rewind — watch what happens.
- **Ambiguities:** Note them, let the run finish, fix the skill for the next run.
- **Timeouts:** Log them, move on.

---

## Cheap Verification Before Full Runs

```bash
manufacturer/venv/bin/pytest manufacturer/tests/test_api/test_day_advance.py -W error
retailer/venv/bin/pytest retailer/tests/test_services/test_purchase_order_sync.py
```

Only after these pass should you spend tokens on a scenario run.
