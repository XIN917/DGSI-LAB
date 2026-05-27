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

| Chart | Lines/Bars | Source Data |
|---|---|---|
| **Inventory** | Parts stock (Mfr), Finished printers (Mfr), Printer stock (Retail) | `metrics` tables in Mfr & Retailer DBs |
| **Prices** | Provider price (one part), Mfr Wholesale, Retailer Retail | `metrics` tables in all three DBs |
| **Fulfillment** | Daily Bar Chart: Placed vs Fulfilled vs Backordered | `metrics` table (Retailer) or `logs/run.csv` |
| **Events** | Strip chart marking start/end of scenario events | Scenario JSON & `logs/run.csv` |

## 2. Interpretation (Causal Chain)

For **every** chart generated, write 2–4 sentences explaining the causal chain. 
*   **Don't just say:** "The line goes up on day 12."
*   **Do explain:** *Why* the line goes up (e.g., "The Retailer raised prices on day 12 because stock levels dropped below the 3-day demand threshold, as seen in the inventory chart.")
*   Identify which agent decision produced the result and whether the signal worked as expected.

## 3. Specific Volatile-Market Questions

Answer these four questions specifically for the `holiday-rush.json` (25-day) run:

1.  **Stock Building**: Did the manufacturer build stock ahead of Black Friday? If yes, how? If no, why not?
2.  **Stockouts**: When stockouts happened, whose decision was the proximate cause? Whose was the root cause?
3.  **Price Dynamics**: Did prices stabilise or oscillate? If they oscillated, what drove the oscillation?
4.  **Bullwhip Effect**: Can you identify a bullwhip moment — a case where demand variance amplified upstream?

## 4. Scenario Comparison

Plot equivalent metrics for the `calm-market` and `holiday-rush` scenarios side-by-side. 
Write a paragraph comparing them: 
*   What do the agents do in one scenario that they do not do in the other?
*   Was the change in behavior a success or a failure?
