# PRD — Supply Chain Simulation: Autonomy and Analysis

> Full assignment brief: `week8.pdf`.

## Overview

An autonomous multi-agent supply chain simulation for 3D printers. Three independent services — Provider, Manufacturer, Retailer — each run by an LLM agent playing a business role. A turn engine orchestrates them through simulated time. Scenarios inject market pressure. Metrics tables capture history for analysis.

The system demonstrates emergent coordination: agents never talk to each other directly. The only shared state is the world encoded in the three databases.

---

## System Architecture

```
Turn Engine
    ├── Retailer Agent (:8003)   ← skill: retail-manager.md
    ├── Manufacturer Agent (:8002) ← skill: manufacturer-manager.md
    └── Provider Agent (:8001)   ← skill: provider-manager.md
```

Each day the turn engine:
1. Generates customer demand (modulated by scenario events)
2. Runs all three agents in parallel (manufacturer operates on previous day's retailer orders)
3. Calls `POST /api/day/advance` on each service
4. Prints a one-line summary and saves per-agent logs

Market signals flow downstream → upstream via the shared databases. No direct agent-to-agent communication.

### Emergent Behaviours to Watch

- **Bullwhip effect**: small demand spike at retailer → bigger order to manufacturer → much bigger order to provider
- **Price wars / collapses**: aggressive price-cutting during low demand
- **Stockout cascades**: one agent's slow reaction blocks everyone downstream

---

## Services

### Provider (:8001)

Parts supply company. Holds raw component stock, fulfills purchase orders from the manufacturer, adjusts prices based on stock pressure.

**CLI commands:**
- `./provider-cli day current`
- `./provider-cli stock`
- `./provider-cli orders list [--status pending]`
- `./provider-cli orders show <id>`
- `./provider-cli restock <product> <quantity>`
- `./provider-cli price set <product> <tier> <price>`

### Manufacturer (:8002)

3D printer factory. Buys parts from provider, produces printers, sells to retailer. Manages production capacity and wholesale pricing.

**CLI commands:**
- `./manufacturer-cli day current`
- `./manufacturer-cli stock`
- `./manufacturer-cli sales orders` / `sales order <id>`
- `./manufacturer-cli production status` / `production release <order_id>`
- `./manufacturer-cli capacity`
- `./manufacturer-cli suppliers list` / `suppliers catalog <name>`
- `./manufacturer-cli purchase list` / `purchase create --supplier <name> --product <id> --qty <n>`
- `./manufacturer-cli price list` / `price set <model> <price>`

**Price floors:** P3D-Classic €163, P3D-Pro €246 (material cost + 15% margin).

### Retailer (:8003)

Retail store selling 3D printers to end customers. Manages stock, fulfills or backlogs customer orders, purchases from manufacturer, sets retail prices.

**CLI commands:**
- `./retailer-cli day current`
- `./retailer-cli inventory`
- `./retailer-cli stock`
- `./retailer-cli customers orders`
- `./retailer-cli customers order <id>`
- `./retailer-cli fulfill <order_id>`
- `./retailer-cli backorder <order_id>`
- `./retailer-cli purchase list`
- `./retailer-cli purchase create <model> <qty>`
- `./retailer-cli price list`
- `./retailer-cli price set <model> <price>`

---

## Agent Skill Files

Each agent is driven by a markdown skill file that defines its role, available commands, constraints, and decision framework.

### `skills/provider-manager.md`

```markdown
# Skill: Provider Manager

## Your Role
You manage a parts supply company. Each simulated day:
1. Process incoming purchase orders from manufacturers
2. Manage your stock (simulated upstream supply)
3. Adjust prices based on stock pressure
4. Ship orders whose lead time has elapsed

## Available Commands

### Check current state
- `./provider-cli day current`
- `./provider-cli stock`
- `./provider-cli catalog`
- `./provider-cli orders list` (optional: `--status pending`)
- `./provider-cli orders show <id>`

### Operations
- `./provider-cli restock <product> <quantity>`
- `./provider-cli price set <product> <tier> <price>`

## DO NOT
- Do NOT call `day advance`. The turn engine does that.
- Do NOT change a tier's price more than 15% in one day.
- Do NOT let any single product go to zero stock if orders for it are pending.

## Decision Framework

1. **Assess.** Run `stock`, `catalog`, and `orders list`. Summarise the state in 2–3 sentences. On Day 1, treat the catalog quantities as the starting levels. On subsequent days, use the highest stock level observed for each product as the baseline.
2. **Restock.** If any product stock is below 50% of its starting level, restock up to the starting level. Execute restock commands immediately — do not ask for confirmation. Log the rationale.
3. **Adjust prices.** If stock of a product is above 150% of starting, lower the top tier price 5–10%. If stock is below 30%, raise it 5–10%. Stay within the 15% daily bound.
4. **Summarise.** 3–5 bullet points of what you did today and why.

## Market Signals

- `supply_modifier < 0.7`: shortage context. Raise prices more aggressively; accept that you may not be able to fulfill all orders.
- `demand_modifier > 1.5`: manufacturer will likely place larger orders. Build stock ahead.
```

### `skills/manufacturer-manager.md`

```markdown
# Skill: Manufacturer Manager

## Your Role
You manage the production of a 3D printer factory. Each simulated day you:
1. Review incoming orders from retailers
2. Check inventory of parts and finished printers
3. Release sales orders to production when materials allow
4. Order parts from suppliers when stock runs low
5. Adjust wholesale prices based on demand vs capacity

## Available Commands

### Check current state
- `./manufacturer-cli day current`
- `./manufacturer-cli stock`
- `./manufacturer-cli sales orders` / `sales order <id>`
- `./manufacturer-cli production status`
- `./manufacturer-cli capacity`

### Purchasing
- `./manufacturer-cli suppliers list`
- `./manufacturer-cli suppliers catalog <supplier_name>`
- `./manufacturer-cli purchase list`
- `./manufacturer-cli purchase create --supplier <name> --product <id> --qty <n>`

### Production
- `./manufacturer-cli production release <order_id>`

### Pricing
- `./manufacturer-cli price list`
- `./manufacturer-cli price set <model> <price>`

## DO NOT
- Do NOT call `day advance`. The turn engine does that.
- Do NOT release more orders than daily capacity allows.
- Do NOT order parts that will arrive after the orders needing them are overdue if a faster supplier exists.

## Decision Framework

1. **Assess.** Run `stock`, `sales orders`, `capacity`, `production status`. Summarise in 2–3 sentences.
2. **Fulfill what you can.** For each pending sales order, if parts are in stock and capacity is available, release it. Prioritise oldest orders.
3. **Order what you need.** For each part below two days of expected consumption, consult `suppliers catalog` and place a purchase order with the best option.
4. **Adjust prices.** If orders exceed capacity by >50% for 2+ days, raise wholesale 5–10%. If utilisation is below 40% for 2+ days, lower 5–10%. Never go below floor (P3D-Classic €163, P3D-Pro €246).
5. **Log your reasoning.** One-line explanation before each mutation.

## Market Signals
- `demand_modifier > 1.5`: high-demand period. Build inventory ahead, consider raising prices.
- `supply_modifier < 0.7`: constrained supply. Place purchase orders earlier and larger.
- No signal / modifier ≈ 1.0: business as usual.

## When Done
Print a 3–5 bullet summary of what you did today and why. Then exit. Do not advance the day.
```

### `skills/retail-manager.md`

```markdown
# Skill: Retail Manager

## Your Role
You manage a retail store that sells 3D printers to end customers. Each simulated day:
1. Fulfill customer orders from stock where possible
2. Mark insufficient-stock orders as backordered
3. Order more printers from the manufacturer if stock is low
4. Set retail prices to balance profit against demand

## Available Commands

### Check current state
- `./retailer-cli day current`
- `./retailer-cli stock`
- `./retailer-cli customers orders`
- `./retailer-cli customers order <id>`

### Fulfillment
- `./retailer-cli fulfill <order_id>`
- `./retailer-cli backorder <order_id>`

### Purchasing
- `./retailer-cli purchase list`
- `./retailer-cli purchase create <model> <qty>`

### Pricing
- `./retailer-cli price list`
- `./retailer-cli price set <model> <price>`

## DO NOT
- Do NOT call `day advance`. The turn engine does that.
- Do NOT set retail price below manufacturer wholesale + 20%.
- Do NOT leave customer orders in `pending`. Every one becomes `fulfilled` or `backordered` by end of turn.

## Decision Framework

1. **Fulfill.** For each pending customer order, fulfill if stock exists, otherwise backorder.
2. **Reorder.** For each model where stock is below 3 days of recent average demand, place a purchase order with the manufacturer.
3. **Price.** If stock is low relative to recent demand, raise price 5%. If stock is piling up (over 5 days supply) and prices are not already at floor, lower price 5%.
4. **Summarise.** Orders fulfilled, backordered, purchases placed, price changes — one line each.

## Market Signals
- `demand_modifier > 1.5`: demand spike incoming. Place larger purchase orders now; prices may still hold.
- `demand_modifier < 0.8`: soft demand. Slow reorders; consider cutting prices.
- `price_sensitivity: high`: customers are shopping around. Be cautious about raising prices.
```

---

## Turn Engine

**Entry point:** `python turn_engine.py config/sim.json scenarios/<file>.json <days> [--model <model_name>] [--start-day N] [--full-skill-prompt]`

Each turn:
1. Read current scenario signal for the day (demand, supply, lead time, price sensitivity modifiers)
2. Generate customer orders at retailer (Poisson-distributed, modulated by `demand_modifier`)
3. On Day 1 only: seed random purchase orders (Classic + Pro) at retailer so manufacturer has pending work from the start
4. Prefetch decision-relevant state for all agents in parallel
5. Run all three agents (Retailer, Manufacturer, Provider) in parallel — manufacturer operates on previous day's retailer orders (realistic 1-day lag)
6. Call `POST /api/day/advance` on each service
7. Save agent output to `logs/{scenario}/day-NNN.log` (consolidated)
8. Print summary line: `Day N: X customer orders / Y fulfilled / Z backordered / W stockout`

At end of run:
- Snapshot `provider.db`, `manufacturer.db`, and `retailer.db` into `logs/{scenario}/`.
- Print run summary table.

**Optimizations**: 
- **Full Parallelization**: All three agents run concurrently, cutting per-day wall time roughly in half.
- **Compact Role Contracts**: Default prompts use concise per-role contracts with hard rules, thresholds, and command syntax. `--full-skill-prompt` restores the original full skill markdown for debugging.
- **Trimmed Prefetch**: Agents receive only decision-relevant state, with long CLI outputs capped to headers, active rows, and recent rows.
- **Action Batching**: Agents treat prefetched state as their assessment step, avoid duplicate read-only commands, batch related mutations into as few Bash turns as practical, and keep final summaries under 120 words.
- **Model Override**: `--model` flag selects the LLM brain. Model availability depends on the active Claude account.
- **Run Chunking**: `--start-day N` resumes long scenarios from day N using the current database state.

**Time-box**: one full run must complete in ≤ ~30 minutes of wall clock. If longer, per-turn prompts are too large or the timeout is too permissive.

---

## Scenario Format

```json
{
  "scenario_name": "string",
  "base_demand": {"mean": 5, "variance": 2},
  "base_price": 400,
  "events": [
    {
      "name": "string",
      "start_day": 1,
      "end_day": 10,
      "demand_modifier": 1.0,
      "supply_modifier": 1.0,
      "lead_time_modifier": 1.0,
      "price_sensitivity": "normal | high",
      "description": "string"
    }
  ]
}
```

**Field semantics:**
- `demand_modifier`: multiplies base customer order rate
- `supply_modifier`: multiplies provider available stock capacity
- `lead_time_modifier`: multiplies provider base lead time during `day advance`
- `price_sensitivity`: passed to agent prompt as a hint (not a hard engine rule)

### `scenarios/calm-market.json`

```json
{
  "scenario_name": "Calm Market — Baseline",
  "base_demand": {"mean": 5, "variance": 1},
  "base_price": 400,
  "events": [
    {
      "name": "normal",
      "start_day": 1,
      "end_day": 15,
      "demand_modifier": 1.0,
      "supply_modifier": 1.0,
      "description": "Steady baseline — no disruptions"
    }
  ]
}
```

### `scenarios/holiday-rush.json`

```json
{
  "scenario_name": "Q4 2026 — Holiday Rush with Chip Shortage",
  "base_demand": {"mean": 5, "variance": 2},
  "base_price": 400,
  "events": [
    { "name": "normal",          "start_day": 1,  "end_day": 10, "demand_modifier": 1.0, "supply_modifier": 1.0 },
    { "name": "black_friday",    "start_day": 11, "end_day": 13, "demand_modifier": 3.0, "supply_modifier": 1.0, "price_sensitivity": "high" },
    { "name": "chip_shortage",   "start_day": 14, "end_day": 20, "demand_modifier": 1.5, "supply_modifier": 0.4, "lead_time_modifier": 2.0 },
    { "name": "christmas_season","start_day": 18, "end_day": 25, "demand_modifier": 2.5, "supply_modifier": 0.6 }
  ]
}
```

Days 18–20 have both `chip_shortage` and `christmas_season` active — modifiers multiply.

### Scenario Design Patterns

- **Slow ramp**: demand builds over 5–7 days. Do agents build stock in time?
- **Sudden shock**: demand triples overnight. Do agents respond or stockout?
- **Combined stress**: demand spikes and suppliers slow down simultaneously. This is when the bullwhip shows up.
- **Quiet period**: demand drops. Do agents lower prices and drain inventory, or panic-buy?

---

## Metrics & Observability

Each service snapshots per-day metrics into a `metrics` table during `POST /api/day/advance`.

| Service | Metrics columns |
|---|---|
| **Provider** | `sim_day`, stock per product, current price per product/tier, orders pending/shipped/delivered today |
| **Manufacturer** | `sim_day`, parts stock, finished-printer stock, production utilisation, wholesale price per model, sales orders pending/completed |
| **Retailer** | `sim_day`, printer stock per model, retail price per model, customer orders placed/fulfilled/backordered |

All `metrics` tables include a `sim_day` integer column. Query by day to produce time-series for charts.

**Four observability requirements:**
1. Per-day agent logs: `logs/{scenario}/day-NNN.log` (one file per day containing all roles)
2. Per-event log in each database's `events` table
3. `metrics` table with `sim_day` in all three databases
4. Turn engine summary line after each day: `Day 7: 12 customer orders / 9 fulfilled / 2 backordered / 1 stockout`

---

## Analysis

Using `matplotlib`, produce **4 charts per scenario**:

1. **Inventory over time** — three lines: parts stock at manufacturer, finished-printer stock at manufacturer, printer stock at retailer
2. **Prices over time** — three lines: provider price (one representative part), manufacturer wholesale, retailer retail
3. **Order fulfillment** — daily bar chart: customer orders placed vs fulfilled vs backordered
4. **Events overlay** — strip chart marking when each scenario event started/ended, aligned with the above

For each chart write 2–4 sentences on the causal chain: not "the line goes up" but *why*, what agent decision produced it, whether the signal worked as expected.

**Scenario comparison**: plot calm vs volatile side-by-side. Write a paragraph: what do agents do in one that they don't in the other, and is that a success or failure?

**Required interpretation questions for the volatile run:**
- Did the manufacturer build stock ahead of Black Friday? If yes, how? If no, why not?
- When stockouts happened, whose decision was the proximate cause? Whose was the root cause?
- Did prices stabilise or oscillate? What drove it?
- Can you identify a bullwhip moment — demand variance amplifying upstream?

---

## Final Deliverables

### GitHub Repository
- `provider/`, `manufacturer/`, `retailer/` — all three service sources
- `turn_engine.py`
- `skills/` — all three skill files
- `scenarios/` — at least two scenario files
- Seed data for every app
- `CLAUDE.md`, `README.md` (reproducible setup + run instructions)
- `.gitignore` excluding: `.env`, `__pycache__/`, `.venv/`, `*.db`, `logs/`
- Clean commit history across all three weeks

### Final Report (5–8 pages, PDF)
Generated via pandoc + mermaid-filter. Four sections:

**a) System architecture** — full system diagram, ER diagram per app, turn engine order of operations, how market signals flow through the system.

**b) Agent design** — summarise each skill file (do not paste in full), decisions made during authoring, skills rewritten after watching agent fail, what agents are good and bad at.

**c) Simulation results** — charts from 15+ day volatile run, calm scenario for comparison, causal-chain interpretation, emergent behaviours explained.

**d) Vibe-coding reflection** — how Claude Code was used across three weeks, what worked, what didn't, one thing to redesign from scratch.

### Presentation (max 10 slides + live demo)
- System overview (one architecture diagram slide)
- Agent design (one slide per role, brief)
- Live demo: 2–3 days of simulation, narrate what agents are doing
- Results: one "most interesting chart" slide
- Reflection: one slide on what you learned

The demo is the most important part. Rehearse it. Keep it short (~3 days for a live run). Have a plan for what to do if agents stall.

---

## Stretch Goals (optional, in order of value)

1. LLM-driven end customers — replace deterministic demand generator with an LLM customer persona
2. Multiple competing retailers with different pricing strategies
3. Regional supply disruption event type (half of providers down for 3 days)
4. LLM-generated scenario JSON from a plain-English description
5. Streamlit live dashboard tailing metrics tables during a run
