# PLAN — Week 8 Implementation

> Product spec: `docs/PRD.md`. This document tracks current state and ordered tasks.

## Current State

| Component | Status |
|---|---|
| Provider service (:8001) | Complete — CLI, metrics table, skill wired, seed fixed |
| Manufacturer service (:8002) | Complete — CLI, metrics table, skill wired; `providers.json` bug fixed; HTTP day advance polls external suppliers |
| Retailer service (:8003) | Complete — CLI aligned to skill file, metrics table, skill wired; in-flight manufacturer POs sync until terminal; stale auth removed |
| Turn engine (`turn_engine.py`) | Complete — parallelization, compaction, model flexibility (Gemini/Gemma/Claude), auto chart generation, run.csv cleared on fresh run, duration in summary log |
| `visualize.py` | Complete — 6 charts per scenario, event shading, small multiples for parts, seed-price filter |
| `api_server.py` | Complete — 15 endpoints, SSE streaming, run persistence, model list |
| `skills/` | All three skill files present and wired in `config/sim.json` |
| `scenarios/` | Both scenario files present (`calm-market.json`, `holiday-rush.json`) |
| `docs/ANALYSIS.md` | Complete — 12 chart interpretations, 4 mandatory questions answered, scenario comparison written |
| `CLAUDE.md` / `README.md` / service READMEs | All up to date |

---

## Task List

### Phase 1 — Wire and fix (blockers before any simulation)

- [x] Update retailer CLI to match skill file commands
- [x] Wire provider and retailer skills in `config/sim.json`
- [x] Fix `todays_signal()`: extract all modifiers, multiply overlapping events
- [x] Apply `lead_time_modifier` during provider `day advance`
- [x] Create `scenarios/calm-market.json` and `scenarios/holiday-rush.json`

### Phase 2 — Metrics tables (required for analysis)

- [x] Add `metrics` table with `sim_day` column to all three service DBs
- [x] Snapshot metrics during `POST /api/day/advance` in each service

### Phase 3 — Test and run

- [x] Create project-level integration and logic tests in `tests/`
- [x] Add Gemini agent unit tests in `tests/test_gemini_agent.py`
- [x] Run 15-day simulation against `calm-market.json` (verified, archived in `demo/calm-market_1/`)
- [x] Run 25-day simulation against `holiday-rush.json` (verified, archived in `logs/holiday-rush/` and `demo/holiday-rush/`)
- [x] Fix delivery-sync regression: manufacturer HTTP advance polls external suppliers; retailer syncs all non-terminal POs
- [x] Add focused regression tests for delivery sync
- [x] Fix retailer `manufacturer_client.py` stale auth (0% fulfillment bug)
- [x] Add Gemma 4 26B support; default model → `gemini-3.1-flash-lite`
- [x] Add `api_server.py` — FastAPI wrapper for frontend integration

### Phase 4 — Analysis & Results

- [x] Implement `visualize.py` — 6 charts per scenario with event shading and small multiples
- [x] Generate charts for both scenarios (in `logs/` and `demo/`)
- [x] Draft written causal interpretation for all 12 charts (`docs/ANALYSIS.md`)
- [x] Answer 4 mandatory questions (stock building, stockout, price dynamics, bullwhip)
- [x] Write scenario comparison paragraph

### Phase 5 — Final Delivery

- [ ] Draft 5–8 page Final Report (PDF) — sections: architecture, agent design, results, vibe-coding reflection

---

## Verification Checklist

- [x] All three skill files tested in isolation
- [x] Both scenario files exist and produce clean runs
- [x] `.gitignore` excludes `.env`, `__pycache__/`, `*.db`, `logs/`
- [x] 15-day calm-market simulation complete — archived in `demo/calm-market_1/`
- [x] 25-day holiday-rush simulation complete — archived in `logs/holiday-rush/` and `demo/holiday-rush/`
- [x] Agent max-turn budgets: retailer 6, manufacturer 8, provider 8
- [x] Delivery-sync regression tests pass: `manufacturer/venv/bin/pytest manufacturer/tests/test_api/test_day_advance.py -W error`
- [x] `logs/run.csv` cleared on fresh run; summary log includes duration, model, day range
- [x] 6 charts per scenario generated: `inventory.png`, `parts_inventory.png`, `prices.png`, `parts_prices.png`, `fulfillment.png`, `events.png`
- [x] Metrics tables non-empty in all three archived DBs (`logs/holiday-rush/*.db`)
- [x] Causal interpretation written for all charts (`docs/ANALYSIS.md`)
- [x] Scenario comparison paragraph written
- [x] `api_server.py` — 15 endpoints, run persistence, SSE streaming
- [x] All venvs consistent: `pytest` in all service venvs, correct paths documented
- [ ] Final report drafted (PDF)
- [ ] Final `.gitignore` and repo polish check before submission
