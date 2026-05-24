# CLAUDE.md — DGSI Week 8: Supply Chain Simulation

## What This Project Is

An autonomous multi-agent supply chain simulation. Three services (Provider, Manufacturer, Retailer) each run by an LLM agent. A turn engine orchestrates them through simulated days. Scenarios inject market pressure. The goal is emergent coordination — agents share no memory and never talk directly; the only shared state is the world in their databases.

Full spec: `docs/PRD.md` | Implementation tasks: `docs/PLAN.md`

---

## Project Structure

```
week-08/
├── provider/          # Parts supplier service (:8001)
├── manufacturer/      # Printer factory service (:8002)
├── retailer/          # Retail store service (:8003)
├── turn_engine.py     # Orchestrates all three agents per simulated day
├── config/sim.json    # Agent wiring (skill files, URLs, paths)
├── scenarios/         # Scenario JSON files (calm-market, holiday-rush)
├── skills/            # Agent skill files (one per role)
├── scripts/           # Setup, start, reset scripts
├── logs/              # Per-turn agent logs (git-ignored)
└── docs/
    ├── PRD.md         # Product spec
    └── PLAN.md        # Task list and current state
```

Each service has its own virtualenv at `<service>/venv/`.

---

## How to Run

See `README.md` for setup, start, simulate, and reset instructions.

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
3. Runs agents: retailer → manufacturer → provider
4. Calls `POST /api/day/advance` on each service
5. Saves output to `logs/day-NNN-[role].log`

All scenario signal fields are parsed (`demand_modifier`, `supply_modifier`, `lead_time_modifier`, `price_sensitivity`). Overlapping events multiply modifiers. Day-end summary line is printed after each turn.

---

## Key Constraints

- **Never call `day advance` directly.** The turn engine does that via `POST /api/day/advance`.
- **Never change skill files to match the CLI.** The skill files are spec; fix the CLI.
- **Overlapping scenario events multiply modifiers** (not last-wins). This is intentional — it produces the bullwhip effect.
- Price floors: P3D-Classic €163, P3D-Pro €246 (manufacturer minimum).
- One simulation run should complete in ≤ 30 minutes wall clock.

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
- Phase 3 (testing) — manufacturer ✓, retailer ✓, provider fix applied (retest pending), full run not yet done
- Phase 4 (analysis) — not started
- Phase 5 (final deliverables) — not started
