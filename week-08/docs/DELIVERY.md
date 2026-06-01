# Final Deliverables & Delivery Plan

This document tracks the tasks required for the final submission of the DGSI Week 8 project, separating "doing the work" from "delivering the results."

## Part 5: Final Report (PDF)
*Target: 5–8 pages, generated via pandoc.*

- [ ] **Section A: System Architecture**
    - [ ] Full system diagram (mermaid/image).
    - [ ] ER diagrams for Provider, Manufacturer, and Retailer.
    - [ ] Turn engine sequence of operations.
    - [ ] Data flow description for market signals.
- [ ] **Section B: Agent Design**
    - [ ] Summaries of the 3 skill files.
    - [ ] Technical decisions made during skill authoring.
    - [ ] Reflections on agent strengths and weaknesses.
- [ ] **Section C: Simulation Results**
    - [ ] Embed 6 charts for `calm-market` (`inventory.png`, `parts_inventory.png`, `prices.png`, `parts_prices.png`, `fulfillment.png`, `events.png`).
    - [ ] Embed 6 charts for `holiday-rush`.
    - [ ] Written causal-chain interpretation (2–4 sentences per chart).
    - [ ] Answers to the 4 mandatory interpretation questions (Stock building, Stockout causes, Price oscillation, Bullwhip effect).
    - [ ] Scenario comparison paragraph.
- [ ] **Section D: Vibe-Coding Reflection**
    - [ ] Usage of Gemini CLI/Claude Code across 3 weeks.
    - [ ] Evaluation of what worked/failed.
    - [ ] Redesign reflection.

## Part 6: Repository Final Polish
- [ ] Final `CLAUDE.md` and `README.md` review.
- [ ] Final `.gitignore` check (ensure no `.db` or `logs/` are tracked).
- [ ] Clean commit history with issue references.
- [ ] Ensure seed data is easily accessible and scripts work on a fresh clone.
- [ ] Run focused delivery-sync regressions before final scenario runs:
    - `cd manufacturer && pytest tests/test_api/test_day_advance.py -W error`
    - `cd retailer && pytest tests/test_services/test_purchase_order_sync.py`
- [ ] Run unit and API tests (no live services needed): `venv/bin/pytest tests/test_simulation_logic.py tests/test_api_server.py -v`
- [ ] Run UI browser tests against live stack: `venv/bin/pytest tests/test_ui_dashboard.py -v --run-ui`
- [ ] After final scenario runs, inspect archived DBs to confirm supplier/manufacturer/retailer deliveries reached terminal states instead of staying stranded in `pending`, `released`, or `waiting_materials`.
