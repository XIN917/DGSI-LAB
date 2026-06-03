# Week 8 Project Requirements

Consolidated requirements derived from `week8.pdf`, `docs/PRD.md`, and project instructions. See `docs/PLAN.md` for current completion status.

## 1. Core Implementation

- **Autonomous Multi-Agent System**: Three independent services (Provider, Manufacturer, Retailer) driven by LLM agents.
- **Zero Direct Communication**: Agents only share state via their respective databases.
- **Turn Engine**: Orchestrates days, injects scenario signals, and advances time.
- **Long-Run Agent Budgets**: Turn engine keeps stable max-turn limits at retailer 6, manufacturer 8, provider 8.
- **Token Controls for Long Runs**: Compact role prompts, capped prefetch output, short summaries, full-skill debug fallback, and `--start-day` chunking.
- **Skill Files**: Authoritative markdown files for Provider, Manufacturer, and Retailer.
    - Provider: 15% price change cap, 50% restock threshold.
    - Retailer: 3-day demand reorder, mandatory fulfill/backorder.
- **Scenario Files**:
    - `scenarios/calm-market.json`: 15-day baseline.
    - `scenarios/holiday-rush.json`: 25-day volatile scenario with overlapping events.

## 2. Observability & Metrics

- **Per-turn Agent Logs**: Saved to `logs/{scenario}/day-NNN.log`.
- **Event Logs**: `events` table in every database must be populated.
- **Numeric Time-Series**: `metrics` table with `sim_day` in every database.
    - Provider: Stock, price, orders (pending/shipped/delivered).
    - Manufacturer: Parts stock, finished stock, utilization, wholesale price, sales orders.
    - Retailer: Printer stock, retail price, customer orders (placed/fulfilled/backordered).
- **Engine Summary**: One-line KPI summary printed after every day.
- **Global Inventory Snapshot**: Day-end table includes Retailer, Manufacturer, and Provider stock.

## 3. Simulation Logic

- **Multiplicative Modifiers**: Overlapping scenario events multiply their modifiers.
- **Lead Time Enforcement**: `lead_time_modifier` correctly scales Provider lead times.
- **Customer Demand**: Generated at Retailer using `random.gauss` influenced by price and demand modifiers.
- **HTTP Day Advance Parity**: Side effects required during simulation advance must exist in HTTP endpoints. Manufacturer HTTP advance polls external suppliers before advancing.
- **Purchase-Order Delivery Sync**: Retailer keeps syncing all non-terminal manufacturer POs until delivered/cancelled.
- **Focused Regression Tests**: Delivery-sync bugs are covered by `manufacturer/tests/test_api/test_day_advance.py` and `retailer/tests/test_services/test_purchase_order_sync.py`.
- **Daily KPI Timing**: Turn Day N customer demand is created before service day advance.

## 4. Analysis Requirements

- **Visualization**: `visualize.py` generates 9 charts per scenario to `logs/{scenario}/charts/` — auto-generated at end of every run.
- **Causal Interpretation**: 2–4 sentences per chart explaining agent decisions (in `docs/ANALYSIS.md` and `report.md §3`).
- **Interpretation Questions** (for `holiday-rush`): stock building ahead of Black Friday, stockout causes, price oscillation drivers, bullwhip moment.
- **Scenario Comparison**: Comparative paragraph (`report.md §3.4`).

## 5. Delivery

- **GitHub Repo**: Clean code, seed data, documentation, and `.gitignore`.
- **Final Report**: 5–8 page PDF generated via pandoc.
