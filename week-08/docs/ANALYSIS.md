# Analysis Requirements & Templates

This document outlines the specific visualization and interpretation requirements for the final report.

## 1. Required Charts

For **each** scenario (`calm-market` and `holiday-rush`), generate the following six charts using `matplotlib`.

**Execution:**
```bash
# To generate from archived data (recommended):
./venv/bin/python visualize.py logs/calm-market
./venv/bin/python visualize.py logs/holiday-rush
```

> **Note:** Charts are auto-generated at the end of each `turn_engine.py` run and saved to `logs/{scenario}/charts/`. The commands above regenerate them from archived data.

| File | Content | Source Data |
|---|---|---|
| `inventory.png` | Finished goods stock — Mfr & Retailer for all models | `metrics` tables in Mfr & Retailer DBs |
| `parts_inventory.png` | Raw materials stock — one subplot per Provider part (small multiples) | `metrics` table in Provider DB |
| `prices.png` | Finished goods pricing — Mfr wholesale & Retailer retail | `metrics` tables in Mfr & Retailer DBs |
| `parts_prices.png` | Part pricing — one subplot per Provider part (small multiples) | `metrics` table in Provider DB |
| `fulfillment.png` | Daily bar chart: Placed vs Fulfilled vs Backordered | `logs/run.csv` |
| `events.png` | Demand/Supply/Lead Time modifiers with event shading | Scenario JSON & `logs/run.csv` |

All charts show **colored event bands**: Black Friday (blue), Chip Shortage (orange), Christmas Rush (purple).

---

## 2. Chart Interpretation

### calm-market (15 days)

#### `inventory.png` — Finished Goods Inventory

Manufacturer Classic stock (blue) begins at 17 units and stays flat until day 6, when a large production batch is released, spiking to 59 units. The retailer draws from this steadily: Retail Classic (green) climbs from near-zero to a peak of 68 units by day 10 as the manufacturer's batch is delivered. After day 10, the manufacturer's Classic stock collapses to ~1 unit — it fulfilled the retailer's purchase orders and stopped producing because finished stock at the retailer was now adequate. The Pro line follows a similar but smaller pattern, stabilising around 41 units wholesale and 35 units retail, reflecting lower base demand.

#### `parts_inventory.png` — Raw Materials Inventory (Provider)

Most parts (Bed Heater, Extruder Kit, PCB Control, Stepper Motor) stay perfectly flat at their seed levels throughout the 15 days — the manufacturer drew so little that the provider never needed to restock them. `Frame Kit` is the exception: it depletes steadily from 450 to ~395 units as it is the primary structural component consumed in every Classic unit produced. `Dual Extruder Kit`, `Hotend`, `Hotend Pro`, `Filament Sensor`, and `Power Supply` all dip in the first 4 days (manufacturer consuming seed stock) then recover sharply around day 4–5 as the provider agent restocks. This confirms the provider is responding to order signals, not pre-emptively stocking up.

#### `prices.png` — Finished Goods Pricing

Manufacturer wholesale prices (blue = Classic at €163, orange = Pro at €246) are flat throughout — the manufacturer never triggered its price-adjustment rule because production utilisation remained moderate and stock never critically low. Retail prices tell a different story: both climb steadily from day 1 (Classic: €1,575 → €2,340; Pro: €2,625 → €2,900), with the retailer raising prices by ~5% roughly every 3–4 days in response to slowly tightening stock. The retailer is using price as a demand-management lever even in a calm market — prices converge and flatten after day 10 once large stock arrives and the urgency drops.

#### `parts_prices.png` — Part Pricing (Provider)

All 11 parts remain at their seed prices for the entire 15-day run — flat horizontal lines. The provider agent found no reason to raise prices because stock levels stayed well above reorder thresholds in calm conditions. This is the expected baseline: provider pricing is inert when the supply chain is healthy.

---

### holiday-rush (25 days)

#### `inventory.png` — Finished Goods Inventory

Days 1–10 (Normal phase): manufacturer builds up Classic stock from 14 to 59 units, anticipating demand. The retailer receives deliveries and holds 0–10 units as it sells through stock daily. Days 11–13 (Black Friday, 3× demand): the manufacturer releases a large batch (peak 89 units Classic), and the retailer's stock rockets to 124 units — the pre-built buffer absorbs the demand spike with no stockout. Days 14–17 (Chip Shortage begins): manufacturer Pro stock collapses from 52 to 7 units as parts dry up; the retailer sits on 80–120 units of finished goods because it over-ordered during Black Friday. Days 18–25 (Christmas + Chip Shortage overlap): demand is 3.75×, but the retailer's large buffer (100+ Classic, 65+ Pro) means it can keep fulfilling without new manufacturer deliveries. Manufacturer Classic stock plateaus at ~44 units — it stopped producing to conserve scarce parts.

#### `parts_inventory.png` — Raw Materials Inventory (Provider)

During Black Friday (days 11–13), provider stock barely moves — demand is on finished goods, not parts, so the manufacturer has not yet placed large replenishment orders. The chip shortage (days 14–20) is immediately visible: `Dual Extruder Kit` and `Hotend Pro` oscillate wildly (0 → 1000 → 400) as the manufacturer floods the provider with emergency purchase orders, the provider restocks, and the manufacturer draws again. `Power Supply` and `Frame Kit` show a similar but less extreme pattern. `Stepper Motor` spikes to 750 on day 25 — a late, large order placed by the manufacturer after it realised its safety stock was exhausted. Parts that saw no price action (Bed Heater, Filament Sensor, PCB Control, Extruder Kit) stayed flat: the manufacturer had sufficient on-hand stock for those throughout.

#### `prices.png` — Finished Goods Pricing

Manufacturer wholesale prices (€163 Classic, €246 Pro) are almost entirely flat — the manufacturer held its floor prices throughout, even during the chip shortage, because it had enough finished stock buffered at the retailer level and did not face direct customer pressure. Retail prices are the main event: both Classic and Pro start around €1,575–2,625 and climb continuously, accelerating through the Christmas+Chip overlap (days 18–25) to reach €3,800–3,900 by day 25. The retailer raised prices by 5–10% per day once demand exceeded 2× and stock began declining, using price as a rationing mechanism. The gap between retail and wholesale widens from ~€1,400 on day 1 to over €3,600 by day 25 — aggressive price gouging enabled by the supply constraint.

#### `parts_prices.png` — Part Pricing (Provider)

Nine of eleven parts stay flat at seed prices throughout. Two parts break out: `Dual Extruder Kit` jumps from €32 to €110 on day 14 (exactly when the chip shortage begins) and `Hotend Pro` jumps from €55 to €110 on day 18. `Power Supply` rises from €19 to €105 starting around day 17. These three price jumps are the provider agent responding to its own stock depletion — it raised tier-1 prices when the manufacturer's emergency bulk orders drained its warehouse. The timing maps precisely to the chip shortage band in the events chart.

#### `fulfillment.png` — Daily Fulfillment

Days 1–4: 100% fill rate, 2–5 orders per day. Days 5–6: backorders appear (yellow bars) as the retailer's initial stock runs low and the first manufacturer delivery has not yet arrived — this is a pure logistics lag, not a shortage. Days 9–11 (pre-Black Friday): the manufacturer's advance production arrives at the retailer; fill rate returns to 100%. Day 11 (Black Friday peak): 10 orders placed, 8 fulfilled, 2 backordered — the only partial-fill day during the actual Black Friday event, confirming the pre-stocking strategy nearly worked. Days 19–23: demand drops sharply to 0–3 orders per day despite 3.75× modifier — the retailer has raised prices so high (€3,000+) that simulated customer demand falls below base levels. Days 24–25: 5 orders fulfilled cleanly as Christmas demand persists but the price cap is reached.

#### `events.png` — Scenario Modifiers

Days 11–13 (Black Friday): demand × 3.0, supply and lead time unchanged. Days 14–20 (Chip Shortage): supply × 0.4, lead time × 2.0, demand drops back to × 1.5. Days 18–20 (overlap): demand multipliers stack to × 3.75 (1.5 × 2.5), supply stays at × 0.4 — this is the most stressful window. Days 21–25 (Christmas alone): demand × 2.5, supply partially recovers to × 0.6. The compounding of demand and supply shocks during days 18–20 is what drives the most dramatic price escalation and the manufacturer's decision to halt production.

---

## 3. Specific Volatile-Market Questions (Holiday-Rush)

**1. Did the manufacturer build stock ahead of Black Friday?**
Yes. Between days 6–10, the manufacturer released two large production batches (Classic peak: 59 units, Pro peak: 52 units) well before the Black Friday window. This proactive build is visible as the inventory spike in `inventory.png` at days 11–12, where the retailer's Classic stock jumps from near zero to 124 units immediately as the delivery arrives. The strategy succeeded: fill rate was 100% on days 9–10 and only 2 orders were backordered on the peak day (day 11).

**2. When stockouts happened, whose decision was the proximate cause? Whose was the root cause?**
The only true backorders (days 5–6 and day 11) were caused proximately by the retailer holding insufficient safety stock before the first manufacturer delivery arrived — a 1-day logistics lag, not a decision error. The deeper pattern in days 19–23 (zero orders fulfilled) was not a stockout: the retailer had 100+ units in stock but prices had risen to €3,000+ which suppressed demand. The root cause of all supply stress was the chip shortage scenario modifier (supply × 0.4 from day 14), which made it impossible for the provider to fully replenish parts regardless of how aggressively the manufacturer ordered.

**3. Did prices stabilise or oscillate?**
Retail prices oscillated continuously upward throughout the run, never stabilising. The retailer raised prices by 5–10% almost every day from day 6 onward, treating each day's stock reading as an independent trigger rather than tracking a trend. This produced a price ratchet: prices never fell even on days when stock was fully replenished. Manufacturer and provider prices remained stable (floor prices) except for the three provider part-price jumps on days 14, 17, and 18, which were one-time step changes in response to stock depletion events rather than oscillation.

**4. Can you identify a bullwhip moment?**
Yes, days 18–21. Retail demand spiked to 3.75× (Christmas + Chip Shortage overlap), but the retailer placed *zero* new purchase orders with the manufacturer because its existing stock buffer was large and prices were already at €2,800. The manufacturer, seeing no new retailer orders, halted production. The provider, seeing no new manufacturer purchase orders, stopped restocking. The actual consumer demand signal (3.75× amplified) was completely invisible to the provider by the time it propagated upstream — the opposite of what the bullwhip predicts. This is a *demand absorption* effect: each tier buffered so aggressively that the upstream tier saw silence when the downstream tier was at peak stress.

---

## 4. Scenario Comparison

The `calm-market` and `holiday-rush` runs use identical agents and skill files — the only difference is the scenario JSON. In calm-market, agents converge to a stable equilibrium within 6–8 days: the manufacturer produces in moderate batches, the retailer holds 30–60 units, and prices climb gently as the retailer applies routine 5% increments. No agent ever faces a decision that conflicts with another's constraints. In holiday-rush, the same agents handle the first shock (Black Friday) correctly — proactive stock building and a near-100% fill rate — but the second shock (chip shortage) exposes the absence of inter-agent communication. The retailer does not know the manufacturer cannot restock; the manufacturer does not know the provider's parts are constrained. Each agent applies its local rule optimally, but the combined effect is a supply chain freeze: manufacturer halts production, retailer raises prices until demand disappears, and provider sits on emergency stock it cannot sell. The calm-market run demonstrates that these agent skill files work — the holiday-rush run demonstrates that they work *locally* but lack a coordination protocol for cascading shocks.
