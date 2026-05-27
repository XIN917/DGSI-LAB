# TESTING — Isolation Tests & Run Log

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
- **Max-Turn Budgets**: Current limits are retailer 4, manufacturer 6, provider 4. Do not reduce them again; lower limits caused provider/manufacturer `Reached max turns` truncation in longer 25-day runs.
**Verdict:** Duration is acceptable for a 15-day run. Further gains should come from a faster model or smaller prompts, not tighter max_turns.
