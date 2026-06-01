# PLAN — Week 8 Implementation

> Product spec: `docs/PRD.md`. This document tracks current state and ordered tasks.

## Current State

| Component | Status |
|---|---|
| Provider service (:8001) | Complete — CLI, metrics table, skill wired, seed fixed |
| Manufacturer service (:8002) | Complete — CLI, metrics table, skill wired; `providers.json` bug fixed; HTTP day advance polls external suppliers |
| Retailer service (:8003) | Complete — CLI aligned to skill file, metrics table, skill wired; in-flight manufacturer POs sync until terminal; stale auth removed |
| Turn engine (`turn_engine.py`) | Complete — parallelization, compaction, model flexibility (Gemini/Gemma/Claude), auto chart generation, per-scenario run.csv (`logs/{scenario}/run.csv`), duration in summary log, Rich console width 150 |
| `visualize.py` | Complete — 9 per-service charts, event shading, single-chart provider views, seed-price filter |
| `api_server.py` | Complete — 15 endpoints, SSE streaming, session-scoped run registry with elapsed_seconds persistence, per-scenario KPI reads from `logs/{scenario}/run.csv` |
| Tests (`tests/`) | Complete — `test_simulation_logic.py` (turn engine), `test_api_server.py` (29 API unit tests via TestClient), `test_ui_dashboard.py` (20 Playwright browser tests, `--run-ui`); `test_integration.py` now resets services before and after to leave services at day 0 |
| `skills/` | All three skill files present and wired in `config/sim.json` |
| `scenarios/` | Both scenario files present (`calm-market.json`, `holiday-rush.json`) |
| `docs/ANALYSIS.md` | Complete — 12 chart interpretations, 4 mandatory questions answered, scenario comparison written |
| Dashboard (`dashboard/`, `frontend/`) | Complete — scenario archive switcher, overview KPI accuracy (fill rate = total fulfilled/orders, backlog = cumulative from CSV), provider in-transit = SHIPPED only, event banner, price drift indicators, sparkline labels, provider card sorted by lowest stock, scroll-reset fix, navbar z-index fix |
| Seed prices | Updated — manufacturer wholesale €195/€290, retail seed €295/€435, floors €163/€246 |
| `CLAUDE.md` / `README.md` / service READMEs | All up to date |

---

## Task List

### Phases 1–4 — Complete

All wiring, metrics tables, tests, simulation runs, visualizations, and analysis are done. See git log for details.

### Phase 5 — Final Delivery

- [ ] Draft 5–8 page Final Report (PDF) — sections: architecture, agent design, results, vibe-coding reflection

---

## Verification Checklist

- [x] All three skill files tested in isolation
- [x] Both scenario files exist and produce clean runs
- [x] `.gitignore` excludes `.env`, `__pycache__/`, `*.db`, `logs/`
- [x] 15-day calm-market simulation complete — archived in `logs/calm-market/`
- [x] 25-day holiday-rush simulation complete — archived in `logs/holiday-rush/`
- [x] Agent max-turn budgets: retailer 6, manufacturer 8, provider 8
- [x] Delivery-sync regression tests pass: `manufacturer/venv/bin/pytest manufacturer/tests/test_api/test_day_advance.py -W error`
- [x] Per-scenario `logs/{scenario}/run.csv` (cleared on fresh run of that scenario); summary log includes duration, model, day range
- [x] 9 charts per scenario generated, separated by service: `provider_stock.png`, `provider_prices.png`, `manufacturer_stock.png`, `manufacturer_prices.png`, `manufacturer_utilisation.png`, `retailer_stock.png`, `retailer_prices.png`, `retailer_fulfillment.png`, `scenario_events.png`
- [x] Metrics tables non-empty in all three archived DBs (`logs/holiday-rush/*.db`)
- [x] Causal interpretation written for all charts (`docs/ANALYSIS.md`)
- [x] Scenario comparison paragraph written
- [x] `api_server.py` — 15 endpoints, run persistence, SSE streaming
- [x] All venvs consistent: `pytest` in all service venvs, correct paths documented
- [x] `test_api_server.py` — 29 unit tests covering all endpoints via FastAPI TestClient (no live services needed)
- [x] `test_ui_dashboard.py` — 20 Playwright browser tests for nav, reset banner, simulation controls, archive view (`--run-ui` flag)
- [x] Dashboard UX fixes: scrollable customer orders (scroll position preserved across refreshes), log content visibility, log dropdown auto-select, elapsed time in run chips (seconds shown, duration bug fixed), "fulfilled d0" display fix, run chips show day range (`d1–10`)
- [x] Dashboard scenario archive view: VIEW dropdown switches between live services and `logs/{scenario}/` archived DBs and run.csv; selection persists across page navigation via sessionStorage
- [x] Dashboard overview page: prominent day counter (large num + total), color-coded KPI tiles (green/yellow/red by thresholds), demand and supply modifier tiles shown when active, alerts div bug fixed (`#ov-charts` was nested inside `.alerts`)
- [x] Dashboard overview KPI accuracy: fill rate = total fulfilled/total orders (matches summary.log); backlog = cumulative from run.csv (not DB snapshot); both suppressed at day 0; fill_rate_series suppressed at day 0
- [x] Provider in-transit arrow counts only SHIPPED orders; CONFIRMED/InProgress are at-provider, not in transit
- [x] Overview tier cards: manufacturer shows only finished goods; provider sorted by lowest stock; sparklines match shown items
- [x] Event banner, price drift indicators (↑/↓), sparkline labels added to overview
- [x] Overview scroll position preserved across 2s refreshes
- [x] Navbar overlap fixed (z-index:100 on topnav; main isolated at z-index:0)
- [x] Integration tests self-contained: `test_integration.py` resets services before and after the module so live services are always left at day 0
- [x] Reset warning updated; reset no longer attempts to delete `logs/run.csv`
- [x] Scenario log archives preserved on reset; stale day logs cleared per-scenario at run start
- [ ] Full end-to-end test run (calm-market + holiday-rush) to verify all recent fixes: run.log, summary.log, charts, cancel, rate-limit retry, log panel refresh, elapsed time in run chips
- [ ] Final report drafted (PDF)
- [ ] Final `.gitignore` and repo polish check before submission
