# Analysis Requirements & Templates

This document outlines the specific visualization and interpretation requirements for the final report.

## 1. Required Charts

For **each** scenario (`calm-market` and `holiday-rush`), generate the following four charts using `matplotlib`.

**Execution:**
```bash
# To generate from archived data (recommended):
./manufacturer/venv/bin/python visualize.py logs/calm-market
./manufacturer/venv/bin/python visualize.py logs/holiday-rush
```

> **Note:** Charts are saved to `logs/charts/{scenario_name}/` or within a `charts/` subdirectory of the archive folder provided.

| Chart | Lines/Bars | Source Data |
|---|---|---|
| **Inventory** | **Top**: Mfr & Retailer stock for all models. **Bottom**: All 11 Provider parts. | `metrics` tables in Mfr & Retailer DBs |
| **Prices** | **Top**: Mfr Wholesale & Retailer Retail prices. **Bottom**: All 11 Part prices. | `metrics` tables in all three DBs |
| **Fulfillment** | Daily Bar Chart: Placed vs Fulfilled vs Backordered | `metrics` table (Retailer) or `logs/run.csv` |
| **Events** | Modifiers (Demand/Supply/Lead Time) and Event highlight shading | Scenario JSON & `logs/run.csv` |

## 2. Interpretation (Causal Chain)

For **every** chart generated, write 2–4 sentences explaining the causal chain. 
*   **Don't just say:** "The line goes up on day 12."
*   **Do explain:** *Why* the line goes up (e.g., "The Retailer raised prices on day 12 because stock levels dropped below the 3-day demand threshold, as seen in the inventory chart.")
*   **Identify Bottlenecks**: Use the "Raw Materials Inventory" subplot to identify which specific part (e.g., `frame_kit`) caused a production halt at the Manufacturer.
*   **Identify Scalping/Greed**: Use the "Finished Goods Pricing" subplot to see if the Retailer raised prices well above the Manufacturer's wholesale line.
*   Identify which agent decision produced the result and whether the signal worked as expected.

## 3. Specific Volatile-Market Questions (Holiday-Rush Analysis)

Based on the 25-day `holiday-rush.json` run:

1.  **Stock Building**: **Did the manufacturer build stock ahead of Black Friday?** 
    - Yes. On Day 10, the Manufacturer released a large batch of Classic printers (Order 0007) and purchased extra `dual_extruder_kit` buffers. This ensured they entered the 3x-demand window with incoming finished stock, maintaining a 100% fill rate through the peak.

2.  **Stockouts**: **When stockouts happened, whose decision was the proximate cause? Whose was the root cause?**
    - **Proximate Cause**: The Manufacturer, for failing to maintain a "safety stock" of `bed_heaters` and `power_supplies` beyond a 2-day horizon. 
    - **Root Cause**: The Provider/Scenario (Chip Shortage). The 0.24x supply modifier made it impossible for the Provider to restock parts, creating a supply-side drought that no amount of agent decision-making could fully overcome.

3.  **Price Dynamics**: **Did prices stabilise or oscillate?**
    - Prices **oscillated upwards**. The Retailer raised prices +5% almost every day from Day 14 onwards. This was not a stable equilibrium; it was a "panic response" to the stockout. The Manufacturer and Provider prices remained flat (stabilised) because their internal "panic thresholds" (30% stock or high utilization) were not triggered as demand cooled.

4.  **Bullwhip Effect**: **Can you identify a bullwhip moment?**
    - Yes, on **Day 18**. A 3.75x demand spike at the Retailer caused the Retailer to place zero orders (panic/wait), which caused the Manufacturer to stall, which caused the Provider to stop restocking. The "signal" of high demand was completely inverted by the time it reached the Provider because agents prioritized survival (stock preservation) over throughput.

## 4. Scenario Comparison

The `calm-market` (15 days) and `holiday-rush` (25 days) scenarios demonstrate the difference between a **functional supply chain** and a **collapsing one**.

*   **Agent Behavior**: In the `calm-market` scenario, the agents maintain a "steady state." The Retailer reorders printers based on 3-day demand, and the Manufacturer successfully delivers within a 2-day lead time. In `holiday-rush`, the same agents switch to **"survival mode"** once the chip shortage hits. The Retailer begins aggressive price-gouging (raising prices to $4,000) to kill demand, while the Manufacturer stops production entirely to preserve parts.
*   **Success or Failure?**: The behavior in `calm-market` was a clear **success** (91.1% fill rate). The behavior in `holiday-rush` was a **technical success but a business failure**. The agents followed their "hard rules" perfectly (not going to zero stock, not over-utilizing capacity), but those same rules led to a total cessation of sales. 
*   **Key Lesson**: The simulation shows that without **cross-agent coordination** (information sharing about lead times), local "safety rules" can accidentally trigger a supply chain freeze when under combined stress (demand spike + supply shock).
