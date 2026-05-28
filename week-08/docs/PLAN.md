# PLAN — Week 8 Implementation

> Product spec: `docs/PRD.md`. This document tracks current state and ordered tasks.

## Current State

| Component | Status |
|---|---|
| Provider service (:8001) | Complete — CLI, metrics table, skill wired, seed fixed |
| Manufacturer service (:8002) | Complete — CLI, metrics table, skill wired; `providers.json` bug fixed; HTTP day advance polls external suppliers |
| Retailer service (:8003) | Complete — CLI aligned to skill file, metrics table, skill wired; in-flight manufacturer POs sync until terminal |
| Turn engine (`turn_engine.py`) | Complete — optimized with parallelization, command batching, model flexibility, scenario-based isolation, global inventory snapshots, stable max-turn budgets, and auto chart generation via `visualize.py` at run end. |
| `skills/` | All three skill files present and wired in `config/sim.json` |
| `scenarios/` | Both scenario files present (`calm-market.json`, `holiday-rush.json`) |
| `CLAUDE.md` / `README.md` / `.gitignore` | All present at repo root |

---

## Task List

### Phase 1 — Wire and fix (blockers before any simulation)

- [x] Update retailer CLI to match skill file commands (rename/add: `stock`, `customers orders`, `customers order <id>`, `purchase list`, `purchase create <model> <qty>`, `price list`, `price set <model> <price>`)
- [x] Wire provider skill in `config/sim.json`: set `"skill": "skills/provider-manager.md"`
- [x] Wire retailer skill in `config/sim.json`: set `"skill": "skills/retail-manager.md"`
- [x] Fix `todays_signal()` in `turn_engine.py`: extract `supply_modifier`, `lead_time_modifier`, `price_sensitivity` (currently only `demand_modifier`)
- [x] Fix overlapping event logic in `todays_signal()`: multiply modifiers instead of last-wins overwrite
- [x] Apply `lead_time_modifier` during provider `day advance` logic
- [x] Add day-end summary line to turn engine after all agents complete
- [x] Create `scenarios/calm-market.json` (spec in `docs/PRD.md`)
- [x] Create `scenarios/holiday-rush.json` (spec in `docs/PRD.md`)

### Phase 2 — Metrics tables (required for analysis)

- [x] Add `metrics` table with `sim_day` column to Provider DB
- [x] Add `metrics` table with `sim_day` column to Manufacturer DB
- [x] Add `metrics` table with `sim_day` column to Retailer DB
- [x] Snapshot metrics during `POST /api/day/advance` in each service
### Phase 3 — Test and run

- [x] Test manufacturer skill in isolation — see `docs/TESTING.md`
- [x] Test retailer skill in isolation — see `docs/TESTING.md`
- [x] Test provider skill in isolation — see `docs/TESTING.md` (required fixes before passing)
- [x] Create project-level integration and logic tests in `tests/`
- [x] Implement `visualize.py` using matplotlib to generate required charts
- [x] Run all three agents together for at least one full day
- [x] Verify simulation health (partial run): metrics captured, `run.csv` populated, databases updated
- [x] Run 15+ day simulation against `calm-market.json` (VERIFIED post-delivery-sync fix: all 15 day logs + archived DBs in `logs/calm-market/`)
- [ ] Run 15+ day simulation against `holiday-rush.json`
- [x] Confirm `logs/{scenario}/day-NNN.log` (one per day, all roles) and `logs/{scenario}-summary.log` written after run
- [x] Verify UI: day banner, agent spinner, compact panels, KPI bar, global state table, run summary table all render correctly
- [x] Verify `logs/run.csv` is written and populated after the run (needed for Phase 4 charts)
- [x] Raise and document agent max-turn budgets after long-run truncation: retailer 6, manufacturer 8, provider 8. Do not reduce these again.
- [x] Reduce long-run token usage: compact role contracts by default, `--full-skill-prompt` debug fallback, capped prefetch output, short final summaries, and `--start-day` run chunking.
- [x] Fix delivery-sync regression: manufacturer HTTP advance polls external suppliers; retailer syncs all non-terminal purchase orders.
- [x] Add cheap regression tests for delivery sync: `manufacturer/tests/test_api/test_day_advance.py` and `retailer/tests/test_services/test_purchase_order_sync.py`.
- [x] Clean warning output for manufacturer regression test (`pytest ... -W error` passes).

### Phase 4 — Analysis & Results
*Refer to `docs/REQUIREMENTS.md` and `docs/ANALYSIS.md` for full specs.*

- [x] Implement `visualize.py` using matplotlib to generate required charts
- [x] Run 15+ day simulation against `calm-market.json` after delivery-sync fixes
- [ ] Run 25-day simulation against `holiday-rush.json`
- [x] Integrate `visualize.py` into `turn_engine.py` — charts auto-generated to `logs/{scenario}/charts/` at end of every run
- [ ] Generate holiday-rush charts (pending 25-day run)
- [ ] Draft written causal interpretation and scenario comparison


### Phase 5 — Final Delivery
*Refer to `docs/DELIVERY.md` for the full submission checklist.*

- [ ] Draft 5-8 page Final Report (PDF)


---

## Verification Checklist

- [x] All three skill files tested in isolation (one day each, other two as stubs)
- [x] Full turn with all three agents runs clean for at least one day
- [x] Both scenario files exist (`calm-market.json`, `holiday-rush.json`)
- [x] `.gitignore` excludes `.env`, `__pycache__/`, `.venv/`, `*.db`, `logs/`
- [x] 15+ day simulation completed against `calm-market.json` after delivery-sync fixes
- [ ] 25-day simulation completed against `holiday-rush.json`
- [ ] UI verified: day banner, spinner, compact panels, KPI bar, global state table, run summary table
- [x] Agent max-turn budgets verified/documented for long runs: retailer 6, manufacturer 8, provider 8
- [x] Focused delivery-sync regression tests pass before full scenario reruns
- [x] `logs/run.csv` and `logs/{scenario}-summary.log` populated after a full run
- [x] `logs/{scenario}/day-NNN.log` written for each day (all three roles in one file) — verified for calm-market
- [ ] Metrics tables non-empty in all three DBs, all include `sim_day` column
- [ ] Event logs in all three databases are non-empty and coherent
- [ ] 4 charts per scenario: inventory, prices, fulfillment, events overlay
- [ ] Scenario comparison paragraph written
- [ ] Final report drafted
