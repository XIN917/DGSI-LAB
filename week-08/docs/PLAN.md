# PLAN — Week 8 Implementation

> Product spec: `docs/PRD.md`. This document tracks current state and ordered tasks.

## Current State

| Component | Status |
|---|---|
| Provider service (:8001) | Running; CLI complete; **no metrics table**; skill file written but not wired in `config/sim.json` |
| Manufacturer service (:8002) | Running, agent-driven; **no metrics table** |
| Retailer service (:8003) | Running; CLI exists but **command names differ from skill file** (see below); **no metrics table**; skill file written but not wired in `config/sim.json` |
| Turn engine (`turn_engine.py`) | Copied from week-07; only `demand_modifier` parsed from scenario events; overlapping events are last-wins (needs multiply); no day-end summary line; log writing logic exists |
| `skills/` | All three skill files present; only `manufacturer-manager.md` wired in `config/sim.json` |
| `scenarios/` | Directory exists but empty |
| `CLAUDE.md` / `README.md` / `.gitignore` | Missing at repo root |

### Retailer CLI Mismatch

The skill files are authoritative (from `week8.pdf`) — the CLI must be updated to match them, not the other way around.

| Skill file command (authoritative) | Actual CLI command (needs fixing) |
|---|---|
| `./retailer-cli stock` | `./retailer-cli inventory` |
| `./retailer-cli customers orders` | `./retailer-cli customer-orders list` |
| `./retailer-cli customers order <id>` | not implemented |
| `./retailer-cli purchase list` | `./retailer-cli purchase-orders list` |
| `./retailer-cli purchase create <model> <qty>` | `./retailer-cli purchase-orders create --sku --quantity` |
| `./retailer-cli price list` | not implemented |
| `./retailer-cli price set <model> <price>` | `./retailer-cli pricing <sku> <price>` |

Provider: `price set <product> <tier> <price>` — CLI uses positional integers (`product_id min_quantity unit_price`). Functionally equivalent but needs to be verified the agent can invoke it correctly.

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

- [ ] Test provider skill in isolation (set other two to stub, run 1 day)
- [ ] Test retailer skill in isolation (set other two to stub, run 1 day)
- [ ] Run all three agents together for at least one full day
- [ ] Run 15+ day simulation against `holiday-rush.json`
- [ ] Run 15+ day simulation against `calm-market.json`
- [ ] Confirm `logs/day-NNN-[role].log` written for all three roles

### Phase 4 — Analysis

- [ ] Generate 4 charts for `holiday-rush` run (inventory, prices, fulfillment, events overlay)
- [ ] Generate 4 charts for `calm-market` run
- [ ] Write scenario comparison paragraph
- [ ] Answer the 4 required interpretation questions

### Phase 5 — Final deliverables

- [ ] Write `README.md` with reproducible setup + run instructions
- [ ] Write `CLAUDE.md`
- [ ] Add root `.gitignore` (exclude `.env`, `__pycache__/`, `.venv/`, `*.db`, `logs/`)
- [ ] Draft presentation slides (10 max)
- [ ] Rehearse live demo (~3 days simulation)
- [ ] Generate final report PDF via pandoc

---

## Verification Checklist

- [ ] All three skill files tested in isolation (one day each, other two as stubs)
- [ ] Full turn with all three agents runs clean for at least one day
- [ ] 15+ day simulation completed against `holiday-rush.json`
- [ ] Both scenario files exist and have been run
- [ ] Metrics tables non-empty in all three DBs, all include `sim_day` column
- [ ] Event logs in all three databases are non-empty and coherent
- [ ] Agent per-turn logs in `logs/` for all three roles
- [ ] 4 charts per scenario: inventory, prices, fulfillment, events overlay
- [ ] Scenario comparison paragraph written
- [ ] `.gitignore` excludes `.env`, `__pycache__/`, `.venv/`, `*.db`, `logs/`
- [ ] Presentation slides drafted, demo rehearsed
