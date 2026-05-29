import matplotlib
matplotlib.use("Agg")
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import json
import os
import sys
from pathlib import Path

# Consistent event colours across all charts
_EVENT_COLORS = {
    "black_friday":    ("#1a6faf", 0.12),
    "chip_shortage":   ("#b84c00", 0.12),
    "christmas_season":("#6a0dad", 0.12),
}
_EVENT_LABELS = {
    "black_friday":    "Black Friday",
    "chip_shortage":   "Chip Shortage",
    "christmas_season":"Christmas Rush",
}
_DEFAULT_EVENT_COLOR = ("#555555", 0.08)


def load_metrics(db_path, table_name):
    if not os.path.exists(db_path):
        print(f"Warning: {db_path} not found.")
        return pd.DataFrame()
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    except Exception as e:
        print(f"Error reading {table_name} from {db_path}: {e}")
        df = pd.DataFrame()
    conn.close()
    return df


def _shade_events(ax, events, alpha_override=None):
    """Draw vertical shaded bands for scenario events on an axis."""
    seen = set()
    for ev in events:
        name = ev.get("name", "")
        color, alpha = _EVENT_COLORS.get(name, _DEFAULT_EVENT_COLOR)
        if alpha_override is not None:
            alpha = alpha_override
        label = _EVENT_LABELS.get(name, name.replace("_", " ").title())
        ax.axvspan(ev["start_day"], ev["end_day"], color=color, alpha=alpha,
                   label=label if name not in seen else "_nolegend_")
        seen.add(name)


def _load_events(scenario_name):
    """Return event list from the scenario JSON, or []."""
    for candidate in [
        Path(f"scenarios/{scenario_name}.json"),
        Path(f"scenarios/{scenario_name.split('_')[0]}.json"),
    ]:
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text())
                return data.get("events", [])
            except Exception:
                pass
    return []


def generate_charts(scenario_name, data_dir=None):
    print(f"Generating charts for {scenario_name}...")

    # 1. Resolve paths
    if data_dir:
        base = Path(data_dir)
        provider_db  = base / "provider.db"
        mfr_db       = base / "manufacturer.db"
        retailer_db  = base / "retailer.db"
        run_csv      = base / "run.csv"
        if not run_csv.exists():
            run_csv = Path("logs/run.csv")
    else:
        provider_db  = Path("provider/data/provider.db")
        mfr_db       = Path("manufacturer/data/manufacturer.db")
        retailer_db  = Path("retailer/data/retailer.db")
        run_csv      = Path("logs/run.csv")

    # 2. Load data
    provider_df = load_metrics(str(provider_db), "metrics")
    mfr_df      = load_metrics(str(mfr_db),      "metrics")
    retailer_df = load_metrics(str(retailer_db),  "metrics")

    run_df = pd.DataFrame()
    if run_csv.exists():
        try:
            full_run_df = pd.read_csv(run_csv)
            run_df = full_run_df[full_run_df["scenario"] == scenario_name]
        except Exception as e:
            print(f"Warning: Could not parse {run_csv}: {e}")

    if data_dir:
        output_dir = Path(data_dir) / "charts"
    else:
        output_dir = Path(f"logs/charts/{scenario_name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 3. Deduplicate
    if not mfr_df.empty:
        mfr_df = mfr_df.groupby(["sim_day", "model_name"], as_index=False).last()
    if not retailer_df.empty:
        retailer_df = retailer_df.groupby(["sim_day", "sku"], as_index=False).last()
    if not provider_df.empty:
        provider_df = provider_df.groupby(["sim_day", "product_name"], as_index=False).last()

    # 4. Load events for shading
    events = _load_events(scenario_name)

    # ── Chart 1: Inventory ────────────────────────────────────────────────────
    if not mfr_df.empty or not retailer_df.empty or not provider_df.empty:

        # --- 1a: Finished goods (single panel) ---
        fig, ax1 = plt.subplots(1, 1, figsize=(12, 5))
        _shade_events(ax1, events)

        if not mfr_df.empty:
            for model in sorted(mfr_df["model_name"].unique()):
                sub = mfr_df[mfr_df["model_name"] == model]
                ax1.plot(sub["sim_day"], sub["finished_stock"],
                         label=f"Mfr {model}", marker="o", alpha=0.85)

        if not retailer_df.empty:
            for sku in sorted(retailer_df["sku"].unique()):
                sub = retailer_df[retailer_df["sku"] == sku]
                ax1.plot(sub["sim_day"], sub["stock_quantity"],
                         label=f"Retail {sku}", marker="s", alpha=0.85)

        ax1.set_title(f"Finished Goods Inventory — {scenario_name}")
        ax1.set_xlabel("Simulation Day")
        ax1.set_ylabel("Units")
        ax1.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize="small")
        ax1.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / "inventory.png", dpi=120)
        plt.close()

        # --- 1b: Raw materials — small multiples ---
        if not provider_df.empty:
            parts = sorted(provider_df["product_name"].unique())
            n = len(parts)
            ncols = 3
            nrows = (n + ncols - 1) // ncols
            fig, axes = plt.subplots(nrows, ncols,
                                     figsize=(5 * ncols, 3.5 * nrows),
                                     sharex=True)
            axes_flat = axes.flatten() if n > 1 else [axes]

            for i, part in enumerate(parts):
                ax = axes_flat[i]
                sub = provider_df[provider_df["product_name"] == part]
                _shade_events(ax, events)
                ax.plot(sub["sim_day"], sub["stock_quantity"],
                        color="#2176ae", linewidth=1.8)
                ax.set_title(part.replace("_", " ").title(), fontsize=9)
                ax.set_ylabel("Units", fontsize=8)
                ax.tick_params(labelsize=8)
                ax.grid(True, alpha=0.3)

            # Hide unused subplots
            for j in range(n, len(axes_flat)):
                axes_flat[j].set_visible(False)

            # Shared x-label
            fig.text(0.5, 0.01, "Simulation Day", ha="center", fontsize=10)
            fig.suptitle(f"Raw Materials Inventory (Provider) — {scenario_name}",
                         fontsize=12, y=1.01)

            # Single event legend at figure level
            if events:
                seen = set()
                handles = []
                for ev in events:
                    name = ev.get("name", "")
                    if name in seen:
                        continue
                    seen.add(name)
                    color, alpha = _EVENT_COLORS.get(name, _DEFAULT_EVENT_COLOR)
                    label = _EVENT_LABELS.get(name, name.replace("_", " ").title())
                    handles.append(mpatches.Patch(color=color, alpha=alpha + 0.3, label=label))
                fig.legend(handles=handles, loc="upper right",
                           bbox_to_anchor=(1.0, 1.0), fontsize=8)

            plt.tight_layout()
            plt.savefig(output_dir / "parts_inventory.png", dpi=120, bbox_inches="tight")
            plt.close()

    # ── Chart 2: Prices ───────────────────────────────────────────────────────
    if not mfr_df.empty or not retailer_df.empty or not provider_df.empty:

        # --- 2a: Finished goods pricing ---
        fig, ax1 = plt.subplots(1, 1, figsize=(12, 5))
        _shade_events(ax1, events)

        if not mfr_df.empty:
            for model in sorted(mfr_df["model_name"].unique()):
                sub = mfr_df[mfr_df["model_name"] == model]
                # Skip day-1 seed anomaly: drop any price > 3× the median
                prices = sub["wholesale_price"].copy()
                med = prices.median()
                prices[prices > 3 * med] = float("nan")
                ax1.plot(sub["sim_day"], prices,
                         label=f"Mfr Wholesale {model}", marker="o", alpha=0.85)

        if not retailer_df.empty:
            for sku in sorted(retailer_df["sku"].unique()):
                sub = retailer_df[retailer_df["sku"] == sku]
                ax1.plot(sub["sim_day"], sub["retail_price"],
                         label=f"Retail {sku}", marker="s", alpha=0.85)

        ax1.set_title(f"Finished Goods Pricing — {scenario_name}")
        ax1.set_xlabel("Simulation Day")
        ax1.set_ylabel("Price (€)")
        ax1.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize="small")
        ax1.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / "prices.png", dpi=120)
        plt.close()

        # --- 2b: Part pricing — small multiples ---
        if not provider_df.empty:
            parts = sorted(provider_df["product_name"].unique())
            n = len(parts)
            ncols = 3
            nrows = (n + ncols - 1) // ncols
            fig, axes = plt.subplots(nrows, ncols,
                                     figsize=(5 * ncols, 3.5 * nrows),
                                     sharex=True)
            axes_flat = axes.flatten() if n > 1 else [axes]

            for i, part in enumerate(parts):
                ax = axes_flat[i]
                sub = provider_df[provider_df["product_name"] == part]
                _shade_events(ax, events)
                ax.plot(sub["sim_day"], sub["price_tier1"],
                        color="#c0392b", linewidth=1.8)
                ax.set_title(part.replace("_", " ").title(), fontsize=9)
                ax.set_ylabel("€", fontsize=8)
                ax.tick_params(labelsize=8)
                ax.grid(True, alpha=0.3)

            for j in range(n, len(axes_flat)):
                axes_flat[j].set_visible(False)

            fig.text(0.5, 0.01, "Simulation Day", ha="center", fontsize=10)
            fig.suptitle(f"Part Pricing (Provider) — {scenario_name}",
                         fontsize=12, y=1.01)

            if events:
                seen = set()
                handles = []
                for ev in events:
                    name = ev.get("name", "")
                    if name in seen:
                        continue
                    seen.add(name)
                    color, alpha = _EVENT_COLORS.get(name, _DEFAULT_EVENT_COLOR)
                    label = _EVENT_LABELS.get(name, name.replace("_", " ").title())
                    handles.append(mpatches.Patch(color=color, alpha=alpha + 0.3, label=label))
                fig.legend(handles=handles, loc="upper right",
                           bbox_to_anchor=(1.0, 1.0), fontsize=8)

            plt.tight_layout()
            plt.savefig(output_dir / "parts_prices.png", dpi=120, bbox_inches="tight")
            plt.close()

    # ── Chart 3: Fulfillment ──────────────────────────────────────────────────
    if not run_df.empty:
        fig, ax = plt.subplots(figsize=(11, 5))
        days = run_df["day"]
        _shade_events(ax, events)
        ax.bar(days, run_df["fulfilled"],   label="Fulfilled",     color="#27ae60", alpha=0.85)
        ax.bar(days, run_df["backordered"], bottom=run_df["fulfilled"],
               label="Backordered", color="#f1c40f", alpha=0.85)
        ax.bar(days, run_df["stockout"],
               bottom=run_df["fulfilled"] + run_df["backordered"],
               label="Lost/Stockout", color="#e74c3c", alpha=0.85)
        ax.plot(days, run_df["orders_placed"],
                color="black", label="Placed Orders", marker=".", zorder=5)
        ax.set_title(f"Daily Fulfillment — {scenario_name}")
        ax.set_xlabel("Simulation Day")
        ax.set_ylabel("Orders")
        ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize="small")
        ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / "fulfillment.png", dpi=120)
        plt.close()

        # ── Chart 4: Events ───────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(11, 4))
        ax.step(days, run_df["demand_mod"], label="Demand Multiplier",    where="post", color="#1a6faf", linewidth=2)
        ax.step(days, run_df["supply_mod"], label="Supply Multiplier",    where="post", color="#e67e22", linewidth=2)
        ax.step(days, run_df["lead_mod"],   label="Lead Time Multiplier", where="post", color="#c0392b", linewidth=2)
        ax.fill_between(days, 0, 1,
                        where=(run_df["demand_mod"] > 1.0),
                        color="#1a6faf", alpha=0.1, label="High Demand")
        _shade_events(ax, events, alpha_override=0.06)
        ax.set_title(f"Scenario Events & Modifiers — {scenario_name}")
        ax.set_xlabel("Simulation Day")
        ax.set_ylabel("Modifier Value")
        ymax = max(run_df["demand_mod"].max(), run_df["supply_mod"].max(), run_df["lead_mod"].max()) + 0.5
        ax.set_ylim(0, ymax)
        ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize="small")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / "events.png", dpi=120)
        plt.close()
    else:
        print(f"Skipping Fulfillment and Events charts for {scenario_name} (no CSV data).")

    print(f"Charts saved to {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
        if data_dir.is_dir():
            scenario = data_dir.name
            generate_charts(scenario, data_dir)
        else:
            print(f"Error: {data_dir} is not a directory.")
    else:
        run_csv_path = Path("logs/run.csv")
        if run_csv_path.exists():
            run_df = pd.read_csv(run_csv_path)
            for s in run_df["scenario"].unique():
                generate_charts(s)
        else:
            print("Error: logs/run.csv not found. Provide a directory path to visualize archived databases.")
