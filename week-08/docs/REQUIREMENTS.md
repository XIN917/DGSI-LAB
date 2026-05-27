# Week 8 Project Requirements

This is the consolidated checklist of all requirements derived from `week8.pdf`, `docs/PRD.md`, and project instructions.

## 1. Core Implementation
- [x] **Autonomous Multi-Agent System**: Three independent services (Provider, Manufacturer, Retailer) driven by LLM agents.
- [x] **Zero Direct Communication**: Agents only share state via their respective databases.
- [x] **Turn Engine**: Orchestrates days, injects scenario signals, and advances time.
- [x] **Long-Run Agent Budgets**: Turn engine keeps stable max-turn limits at retailer 4, manufacturer 6, provider 4; do not reduce these because lower values truncate valid decisions in longer runs.
- [x] **Token Controls for Long Runs**: Compact role prompts, capped prefetch output, short summaries, full-skill debug fallback, and `--start-day` chunking.
- [x] **Skill Files**: Authoritative markdown files for Provider, Manufacturer, and Retailer.
    - [x] Provider: 15% price change cap, 50% restock threshold.
    - [x] Retailer: 3-day demand reorder, mandatory fulfill/backorder.
- [x] **Scenario Files**: 
    - [x] `scenarios/calm-market.json`: 15-day baseline.
    - [x] `scenarios/holiday-rush.json`: 25-day volatile scenario with overlapping events.

## 2. Observability & Metrics
- [x] **Per-turn Agent Logs**: Saved to `logs/{scenario}/day-NNN.log`.
- [x] **Event Logs**: `events` table in every database must be populated.
- [x] **Numeric Time-Series**: `metrics` table with `sim_day` in every database.
    - [x] Provider: Stock, price, orders (pending/shipped/delivered).
    - [x] Manufacturer: Parts stock, finished stock, utilization, wholesale price, sales orders.
    - [x] Retailer: Printer stock, retail price, customer orders (placed/fulfilled/backordered).
- [x] **Engine Summary**: One-line KPI summary printed after every day.
- [x] **Global Inventory Snapshot**: Day-end table includes Retailer, Manufacturer, and Provider stock.

## 3. Simulation Logic
- [x] **Multiplicative Modifiers**: Overlapping scenario events multiply their modifiers.
- [x] **Lead Time Enforcement**: `lead_time_modifier` correctly scales Provider lead times.
- [x] **Customer Demand**: Generated at Retailer using `random.gauss` influenced by price and demand modifiers.

## 4. Analysis Requirements
- [ ] **Visualization**: Script (`visualize.py`) using `matplotlib` to generate 4 charts per scenario:
    1. **Inventory**: Mfr Parts, Mfr Finished, Retailer Stock.
    2. **Prices**: Provider (1 part), Mfr Wholesale, Retailer Retail.
    3. **Order Fulfillment**: Bar chart of Placed vs Fulfilled vs Backordered.
    4. **Events Overlay**: Strip chart aligned with the timeline.
- [ ] **Causal Interpretation**: 2–4 sentences per chart explaining the *why* (agent decisions).
- [ ] **Interpretation Questions** (for `holiday-rush`):
    - [ ] Did the manufacturer build stock ahead of Black Friday?
    - [ ] Proximate vs Root cause of stockouts.
    - [ ] Price stabilization vs oscillation drivers.
    - [ ] Identification of Bullwhip moments.
- [ ] **Scenario Comparison**: Side-by-side metrics plot and comparative paragraph.

## 5. Delivery
- [ ] **GitHub Repo**: Clean code, seed data, documentation, and `.gitignore`.
- [ ] **Final Report**: 5–8 page PDF (Pandoc).
- [ ] **Presentation**: 10 slides + 3-day live demo.
