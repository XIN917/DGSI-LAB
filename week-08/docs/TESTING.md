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

_(to be filled after full simulation runs)_
