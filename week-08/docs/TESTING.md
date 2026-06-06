# TESTING — Test Suite & Run Log

---

## Automated Test Suite

### Quick reference

```bash
# Unit + API tests (no live services required)
venv/bin/pytest tests/test_simulation_logic.py tests/test_api_server.py -v

# Integration tests (requires all 3 services running — auto-resets before and after)
venv/bin/pytest tests/test_integration.py -v

# Full project-level suite (integration tests skipped if services not running)
venv/bin/pytest tests/ -v

# UI browser tests (requires full stack running — see README step 7)
venv/bin/pytest tests/test_ui_dashboard.py -v --run-ui

# Delivery-sync regression tests (run before any full scenario run)
manufacturer/venv/bin/pytest manufacturer/tests/test_api/test_day_advance.py -W error
retailer/venv/bin/pytest retailer/tests/test_services/test_purchase_order_sync.py
```

### Test files

| File | Scope | Tool | Live services? |
|---|---|---|---|
| `tests/test_simulation_logic.py` | Turn engine helpers: signal parsing, compact output, role contracts, modifier multiplication | pytest | No |
| `tests/test_api_server.py` | All 15 `api_server.py` endpoints — scenarios, models, run lifecycle, logs, KPIs, charts, reset | FastAPI TestClient | No |
| `tests/test_integration.py` | Full day-advance cycle across all 3 services, metrics snapshots, lead-time modifier; auto-resets services before and after | pytest-asyncio | Yes |
| `tests/test_ui_dashboard.py` | 20 browser tests — page loads, nav active state, reset banner (idle/running/done/autohide), simulation controls, archive VIEW dropdown | Playwright (headless Chromium) | Yes (`--run-ui`) |
| `manufacturer/tests/test_api/test_day_advance.py` | HTTP day advance polls external suppliers before advancing | pytest | No |
| `retailer/tests/test_services/test_purchase_order_sync.py` | In-flight POs sync until terminal (not just `pending`) | pytest | No |

### `--run-ui` flag

UI tests are skipped by default so `venv/bin/pytest tests/` always passes in environments without a running dashboard. Pass `--run-ui` to enable them — the full stack (services + `api_server.py` + `dashboard.py`) must be running first.

### Playwright installation

Playwright is installed in the root `venv/` (not system Python):

```bash
venv/bin/pip install pytest-playwright
venv/bin/python -m playwright install chromium
```

---

## Isolation Tests

### Manufacturer — Day 1 (calm-market)

**Result:** Pass

**Observations:**
- Correctly identified no sales orders on Day 1 and held production
- Raw materials well-stocked (150+ bed_heaters, 120+ frame_kits, 200+ PCB controls)
- Prices held — correctly applied the 2-day utilisation rule from the skill file
- Noticed supplier list was empty and flagged it; will need orders before purchasing
- `P3D-Classic` wholesale price shown as €1200 — unusually high vs €163 floor; worth monitoring in full run

---

### Retailer — Day 1 (calm-market)

**Result:** Pass

**Observations:**
- Decision framework followed correctly: Fulfill → Reorder → Price → Summarise
- 11 customer orders processed: 7 fulfilled (5 Classic + 2 Pro), 4 backordered (Classic)
- Reorder triggered correctly: stock below 3-day demand, placed 15 Classic + 15 Pro purchase orders
- Prices raised +5% on both models in response to low stock — correct signal response
- Purchase orders sent to manufacturer which was stubbed — POs will be pending until full run

---

### Provider — Day 1 (calm-market)

**Result:** Pass (after fixes)

**Issues found:**
- First run: DB empty — `seed-provider.json` was missing from `provider/data/` (git-ignored folder)
- Second run: seed file found but catalog still empty — seed path was wrong
- **Fix applied:** seed file created at `provider/seed/seed-provider.json`; seed service updated to read from new path; skill updated to run `catalog` in Assess step and infer starting levels from it

**Observations (after fix):**
- Catalog read correctly: 11 products, lead times 2–5 days, tiered pricing
- No restocking needed — all products at starting levels (3,500 units total)
- No price adjustments — normal market signal, no pressure
- Clean 4-bullet summary, no stalling or asking for confirmation

---

## Full Run Log

### Day 1 — All Three Agents Together (calm-market)

**Result:** Pass

**Provider:**
- Baseline day, all modifiers 1.0 — correctly took no action
- Stock at starting levels, no price adjustments
- Ready to receive and fulfill incoming orders

**Manufacturer:**
- Released both retailer orders: #0001 (12× P3D-Classic) and #0002 (12× P3D-Pro) into production
- Suppliers list empty on Day 1 — correctly flagged and skipped purchasing (no orders at provider yet)
- Pricing skipped correctly — 2-day capacity utilisation rule requires prior history
- Watch: if suppliers list stays empty on Day 2+, raw material purchasing will be blocked

**Retailer:**
- Fulfilled 2 customer orders; no pending orders remaining
- Placed restock POs: 12× P3D-Classic + 12× P3D-Pro (3-day supply target)
- Prices held at €500 — normal demand, healthy margins

**Next:** Run full 25-day `holiday-rush` simulation.

---

### calm-market — 15-day full run (first attempt)

**Result:** Failed — procurement broken throughout

**Issue found:**
- `manufacturer/data/providers.json` was missing (the `data/` directory is git-ignored)
- `sync_providers()` reads this file to register ChipSupply (:8001) as an external supplier; without it the suppliers list returns empty on every day
- Manufacturer agent correctly flagged the gap each day but could not place any purchase orders — the entire manufacturer → provider procurement chain was broken for all 15 days
- Retailer showed a `00.0` price display error on day 7 (agent misread truncated CLI output); self-corrected to a valid price

**Fix applied:**
- Moved `providers.json` to `manufacturer/providers.json` (outside the git-ignored `data/` directory)
- Updated `PROVIDERS_JSON_PATH` in `manufacturer/app/core/config.py` to point to the new location
- File is now tracked in git and will survive fresh clones and resets

**Next:** Reset and re-run `calm-market` (15 days) to get a clean run with procurement working, then run `holiday-rush` (25 days).

---

### calm-market — 15-day full run (second attempt)

**Result:** Partial — simulation completed but Manufacturer stuck on Day 2

**Issue found:**
- `AttributeError: 'ProductModel' object has no attribute 'model_name'` occurred during `POST /api/day/advance` on the manufacturer service.
- This happened during the metrics snapshot phase *after* the database day counter was updated but *before* the state was persisted to the simulation state table.
- Result: The manufacturer's database state (specifically the `current_day`) was never persisted beyond Day 2. The manufacturer "lived" Day 2 fifteen times in a row, never triggering logic that required multiple days of history (like price adjustments).
- Overall fulfillment was still 88.3% because the retailer and provider were functioning correctly, and the manufacturer was still processing orders based on the transient day advance (which was committed partially).

**Fix applied:**
- Updated `manufacturer/app/services/simulation_engine.py` to use `product.id` instead of the non-existent `product.model_name`.

**Next:** Reset and re-run `calm-market` (15 days) for a clean baseline, then `holiday-rush` (25 days).

---

### calm-market — 15-day full run (delivery-sync bug found)

**Result:** Completed, but stock flow was incoherent.

**Issue found:**
- Provider orders were delivered in the provider DB, but manufacturer external purchase orders stayed `pending` with `quantity_delivered = 0`.
- Manufacturer raw-material inventory therefore stayed frozen while provider stock decreased.
- Root cause: the turn engine advances services through HTTP `POST /api/day/advance`, but external supplier polling existed only in `manufacturer-cli day advance`.
- Retailer POs could also get stranded: local POs moved from `pending` to statuses such as `released` or `waiting_materials`, but retailer delivery sync only queried `status == "pending"`, so later manufacturer delivery was skipped forever.

**Fix applied:**
- Manufacturer HTTP day advance now calls `ExternalSupplierService.poll_orders()` before `SimulationEngine.advance_day()` in both `/api/day/advance` and `/api/simulation/advance`.
- Retailer purchase-order delivery sync now checks all non-terminal POs (`not delivered/cancelled`) instead of only `pending`.
- Added focused regression tests so this can be verified without spending tokens on a full LLM simulation.

**Fast verification:**
```bash
cd manufacturer
pytest tests/test_api/test_day_advance.py -W error

cd ../retailer
pytest tests/test_services/test_purchase_order_sync.py
```

**Expected result:** manufacturer test reports `2 passed` with no warnings under `-W error`; retailer test reports `1 passed`.

**Next:** Optional low-cost smoke test is a 3-5 day calm-market run, then inspect archived SQLite DBs for manufacturer POs becoming `delivered` and retailer POs receiving `received_day`.

---

### calm-market — 15-day full run (Successful)

**Result:** Pass (Stable baseline established)

**Observations:**
- **Steady State**: Handled a total of 56 customer orders with a **91.1% overall fill rate**.
- **Temporary Stockout**: On Day 6-7, the Retailer experienced a minor stockout (5 units backordered). This was quickly resolved as manufacturer purchase orders were delivered.
- **In-flight Syncing**: Confirmed that Retailer synced manufacturer deliveries correctly across multiple turns, preventing the stranded-PO bug seen in earlier attempts.
- **Stability**: Unlike the holiday-rush, prices remained stable (€1,500–€1,700) because inventory pressure never hit the extreme panic thresholds.

---

### holiday-rush — 25-day full run (Successful)

**Result:** Pass (Scenario successfully reproduced supply chain stress)

**Observations:**
- **Days 11–13 (Black Friday)**: Successfully handled 3.0x demand spike with 100% fill rate. Retailer raised prices +5% daily but inventory remained healthy due to pre-emptive manufacturer releases.
- **Days 14–20 (Chip Shortage)**: Supply-side shock (0.4x supply, 2.0x lead time) caused a major bottleneck. Manufacturer reported "blocked" releases due to frame/hotend shortages.
- **Days 18–25 (Christmas Crunch)**: Combined demand spike (3.75x) on top of the existing shortage led to a **total supply chain collapse**. Fill rates dropped to 0–20% in the final days.
- **Price Elasticity working**: Retailer raised prices to ~$4,000 for Pro models. This successfully "killed" demand (orders dropped to 1–2 per day), proving the engine's price-demand penalty was balancing the market.
- **Bullwhip Effect**: Small fluctuations in retailer pricing created huge swings in upstream backorders, eventually leaving the Manufacturer with a massive backlog they couldn't fulfill.

**Verdict:** The simulation is stable and provides high-quality data for causal analysis. No further logic fixes required.

---

## Performance Analysis

### 15-day Run Duration (approx. 7m - 10m)

**Observation:** Roughly 25s-50s per simulated day (variance driven by LLM response time).
**Analysis:** Optimized architecture:
- **Full Parallelization**: All three agents run concurrently each day; per-day time is bounded by the slowest single agent.
- **Trimmed Prefetch**: Agents receive only decision-relevant state, reducing prompt token count.
- **Day 1 Seed**: Random purchase orders injected before Day 1 agents run, so manufacturer has pending work from the start.
- **LLM Latency**: Single parallel phase per day (approx. 20s-50s depending on agent complexity).
- **Token Controls**: Normal runs use compact role contracts, capped prefetch output, and short final summaries. Use `--full-skill-prompt` only for debugging.
- **Chunking**: Use `--start-day N` to resume a long scenario after session limits without rerunning earlier days.
- **Max-Turn Budgets**: Current limits are retailer 6, manufacturer 8, provider 8. These were raised after day-9 calm-market truncation revealed that lower values cut off valid provider/manufacturer decisions in longer runs.
- **Regression-first workflow**: Before spending tokens on 15/25-day runs, run the focused delivery-sync tests above. They verify the two integration points that caused provider stock, manufacturer stock, and retailer fulfillment to diverge.
**Verdict:** Duration is acceptable for a 15-day run. Further gains should come from a faster model or smaller prompts, not tighter max_turns.
