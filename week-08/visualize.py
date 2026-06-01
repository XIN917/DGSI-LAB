import matplotlib
matplotlib.use("Agg")
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import json
import sys
from pathlib import Path

# Colour palette matching the dashboard
_COLORS = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948"]

_EVENT_COLORS = {
    "black_friday":     ("#1a6faf", 0.12),
    "chip_shortage":    ("#b84c00", 0.12),
    "christmas_season": ("#6a0dad", 0.12),
    "flash_sale":       ("#c0392b", 0.14),
}
_EVENT_LABELS = {
    "black_friday":     "Black Friday",
    "chip_shortage":    "Chip Shortage",
    "christmas_season": "Christmas Rush",
    "flash_sale":       "Flash Sale",
}
_DEFAULT_EVENT_COLOR = ("#555555", 0.08)


def _load_db(db_path):
    if not Path(db_path).exists():
        return pd.DataFrame()
    conn = sqlite3.connect(str(db_path))
    try:
        df = pd.read_sql_query("SELECT * FROM metrics", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def _load_events(scenario_name):
    for candidate in [
        Path(f"scenarios/{scenario_name}.json"),
        Path(f"scenarios/{scenario_name.split('_')[0]}.json"),
    ]:
        if candidate.exists():
            try:
                return json.loads(candidate.read_text()).get("events", [])
            except Exception:
                pass
    return []


def _shade_events(ax, events):
    seen = set()
    for ev in events:
        name = ev.get("name", "")
        color, alpha = _EVENT_COLORS.get(name, _DEFAULT_EVENT_COLOR)
        label = _EVENT_LABELS.get(name, name.replace("_", " ").title())
        ax.axvspan(ev["start_day"], ev["end_day"], color=color, alpha=alpha,
                   label=label if name not in seen else "_nolegend_")
        seen.add(name)


def _event_legend_handles(events):
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
    return handles


def _savefig(fig, path):
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {path}")


def _line(ax, days, values, label, color, marker=None):
    ax.plot(days, values, label=label, color=color,
            linewidth=1.8, marker=marker, markersize=4, alpha=0.9)


def _finish(ax, events, ylabel, title):
    _shade_events(ax, events)
    ax.set_title(title, fontsize=11, fontweight="bold", pad=8)
    ax.set_xlabel("Day", fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.tick_params(labelsize=8)
    ax.grid(True, alpha=0.25, linestyle="--")
    # Series handles only (no event shading in legend — shading is self-explanatory)
    handles, labels = ax.get_legend_handles_labels()
    # Filter out axvspan entries added by _shade_events
    series = [(h, l) for h, l in zip(handles, labels) if not isinstance(h, mpatches.Patch)]
    ev_handles = _event_legend_handles(events)
    if series or ev_handles:
        sh, sl = zip(*series) if series else ([], [])
        ax.legend(list(sh) + ev_handles, list(sl) + [h.get_label() for h in ev_handles],
                  fontsize=8, loc="upper left", framealpha=0.8)


# ── Provider ──────────────────────────────────────────────────────────────────

def _provider_charts(df, events, out_dir, scenario):
    if df.empty:
        return

    df = df.groupby(["sim_day", "product_name"], as_index=False).last()
    parts = sorted(df["product_name"].unique())

    # All parts stock on one chart
    fig, ax = plt.subplots(figsize=(11, 4))
    for i, part in enumerate(parts):
        sub = df[df["product_name"] == part]
        _line(ax, sub["sim_day"], sub["stock_quantity"],
              part.replace("_", " ").title(), _COLORS[i % len(_COLORS)])
    _finish(ax, events, "Units", f"Provider — Parts Stock  [{scenario}]")
    plt.tight_layout()
    _savefig(fig, out_dir / "provider_stock.png")

    # All parts tier-1 price on one chart
    if "price_tier1" not in df.columns:
        return
    fig, ax = plt.subplots(figsize=(11, 4))
    for i, part in enumerate(parts):
        sub = df[df["product_name"] == part]
        _line(ax, sub["sim_day"], sub["price_tier1"],
              part.replace("_", " ").title(), _COLORS[i % len(_COLORS)])
    _finish(ax, events, "€", f"Provider — Parts Prices  [{scenario}]")
    plt.tight_layout()
    _savefig(fig, out_dir / "provider_prices.png")


# ── Manufacturer ──────────────────────────────────────────────────────────────

def _manufacturer_charts(df, events, out_dir, scenario):
    if df.empty:
        return

    df = df.groupby(["sim_day", "model_name"], as_index=False).last()
    models = sorted(df["model_name"].unique())

    # Finished stock
    fig, ax = plt.subplots(figsize=(10, 4))
    for i, m in enumerate(models):
        sub = df[df["model_name"] == m]
        _line(ax, sub["sim_day"], sub["finished_stock"], m, _COLORS[i % len(_COLORS)], marker="o")
    _finish(ax, events, "Units", f"Manufacturer — Finished Stock  [{scenario}]")
    plt.tight_layout()
    _savefig(fig, out_dir / "manufacturer_stock.png")

    # Wholesale price (suppress day-1 seed anomaly > 3× median)
    fig, ax = plt.subplots(figsize=(10, 4))
    for i, m in enumerate(models):
        sub = df[df["model_name"] == m].copy()
        prices = sub["wholesale_price"].copy()
        med = prices.median()
        prices[prices > 3 * med] = float("nan")
        _line(ax, sub["sim_day"], prices, m, _COLORS[i % len(_COLORS)], marker="o")
    _finish(ax, events, "€", f"Manufacturer — Wholesale Price  [{scenario}]")
    plt.tight_layout()
    _savefig(fig, out_dir / "manufacturer_prices.png")

    # Production utilisation
    util_col = next((c for c in ("utilisation_pct", "production_utilisation") if c in df.columns), None)
    if util_col:
        fig, ax = plt.subplots(figsize=(10, 4))
        for i, m in enumerate(models):
            sub = df[df["model_name"] == m]
            vals = sub[util_col] * 100 if sub[util_col].max() <= 1.0 else sub[util_col]
            _line(ax, sub["sim_day"], vals, m, _COLORS[i % len(_COLORS)])
        all_vals = df[util_col] * 100 if df[util_col].max() <= 1.0 else df[util_col]
        ymax = max(all_vals.max() * 1.2, 10)
        ax.set_ylim(0, max(ymax, 110) if ymax > 80 else ymax)
        if ymax > 80:
            ax.axhline(100, color="#e15759", linestyle="--", linewidth=1, alpha=0.6, label="100% capacity")
        _finish(ax, events, "%", f"Manufacturer — Production Utilisation  [{scenario}]")
        plt.tight_layout()
        _savefig(fig, out_dir / "manufacturer_utilisation.png")


# ── Retailer ──────────────────────────────────────────────────────────────────

def _retailer_charts(df, run_df, events, out_dir, scenario):
    if not df.empty:
        df = df.groupby(["sim_day", "sku"], as_index=False).last()
        skus = sorted(df["sku"].unique())

        # Stock per SKU
        fig, ax = plt.subplots(figsize=(10, 4))
        for i, sku in enumerate(skus):
            sub = df[df["sku"] == sku]
            _line(ax, sub["sim_day"], sub["stock_quantity"], sku, _COLORS[i % len(_COLORS)], marker="s")
        _finish(ax, events, "Units", f"Retailer — Inventory  [{scenario}]")
        plt.tight_layout()
        _savefig(fig, out_dir / "retailer_stock.png")

        # Retail price
        fig, ax = plt.subplots(figsize=(10, 4))
        for i, sku in enumerate(skus):
            sub = df[df["sku"] == sku]
            _line(ax, sub["sim_day"], sub["retail_price"], sku, _COLORS[i % len(_COLORS)], marker="s")
        _finish(ax, events, "€", f"Retailer — Retail Price  [{scenario}]")
        plt.tight_layout()
        _savefig(fig, out_dir / "retailer_prices.png")

    # Fulfillment (requires run.csv)
    if not run_df.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        days = run_df["day"]
        _shade_events(ax, events)
        ax.bar(days, run_df["fulfilled"],   label="Fulfilled",     color="#59a14f", alpha=0.85)
        ax.bar(days, run_df["backordered"], bottom=run_df["fulfilled"],
               label="Backordered", color="#edc948", alpha=0.85)
        ax.bar(days, run_df["stockout"],
               bottom=run_df["fulfilled"] + run_df["backordered"],
               label="Lost/Stockout", color="#e15759", alpha=0.85)
        ax.plot(days, run_df["orders_placed"], color="#4e79a7",
                label="Orders Placed", marker=".", linewidth=1.5, zorder=5)
        ev_handles = _event_legend_handles(events)
        handles, labels = ax.get_legend_handles_labels()
        series = [(h, l) for h, l in zip(handles, labels) if not isinstance(h, mpatches.Patch)]
        sh, sl = zip(*series) if series else ([], [])
        ax.legend(list(sh) + ev_handles, list(sl) + [h.get_label() for h in ev_handles],
                  fontsize=8, loc="upper left", framealpha=0.8)
        ax.set_title(f"Retailer — Daily Fulfillment  [{scenario}]",
                     fontsize=11, fontweight="bold", pad=8)
        ax.set_xlabel("Day", fontsize=9)
        ax.set_ylabel("Orders", fontsize=9)
        ax.tick_params(labelsize=8)
        ax.grid(axis="y", alpha=0.25, linestyle="--")
        plt.tight_layout()
        _savefig(fig, out_dir / "retailer_fulfillment.png")

        # Scenario events
        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.step(days, run_df["demand_mod"], label="Demand",    where="post", color=_COLORS[0], linewidth=2)
        ax.step(days, run_df["supply_mod"], label="Supply",    where="post", color=_COLORS[1], linewidth=2)
        ax.step(days, run_df["lead_mod"],   label="Lead Time", where="post", color=_COLORS[2], linewidth=2)
        _shade_events(ax, events)
        ymax = max(run_df["demand_mod"].max(), run_df["supply_mod"].max(),
                   run_df["lead_mod"].max()) + 0.4
        ax.set_ylim(0, ymax)
        ax.set_title(f"Scenario Modifiers  [{scenario}]", fontsize=11, fontweight="bold", pad=8)
        ax.set_xlabel("Day", fontsize=9)
        ax.set_ylabel("Multiplier", fontsize=9)
        ax.tick_params(labelsize=8)
        ax.grid(True, alpha=0.25, linestyle="--")
        handles, labels = ax.get_legend_handles_labels()
        ev_handles = _event_legend_handles(events)
        series = [(h, l) for h, l in zip(handles, labels) if not isinstance(h, mpatches.Patch)]
        sh, sl = zip(*series) if series else ([], [])
        ax.legend(list(sh) + ev_handles, list(sl) + [h.get_label() for h in ev_handles],
                  fontsize=8, loc="upper left", framealpha=0.8)
        plt.tight_layout()
        _savefig(fig, out_dir / "scenario_events.png")


# ── Public entry point ────────────────────────────────────────────────────────

def generate_charts(scenario_name, data_dir=None):
    print(f"Generating charts for {scenario_name}...")

    if data_dir:
        base = Path(data_dir)
        provider_db  = base / "provider.db"
        mfr_db       = base / "manufacturer.db"
        retailer_db  = base / "retailer.db"
        run_csv      = base / "run.csv"
        out_dir = base / "charts"
    else:
        provider_db  = Path("provider/data/provider.db")
        mfr_db       = Path("manufacturer/data/manufacturer.db")
        retailer_db  = Path("retailer/data/retailer.db")
        run_csv      = Path("logs/run.csv")
        out_dir      = Path(f"logs/charts/{scenario_name}")

    out_dir.mkdir(parents=True, exist_ok=True)

    provider_df  = _load_db(provider_db)
    mfr_df       = _load_db(mfr_db)
    retailer_df  = _load_db(retailer_db)

    run_df = pd.DataFrame()
    if run_csv.exists():
        try:
            full = pd.read_csv(run_csv)
            run_df = full[full["scenario"] == scenario_name]
        except Exception as e:
            print(f"  warning: could not read {run_csv}: {e}")

    events = _load_events(scenario_name)

    _provider_charts(provider_df, events, out_dir, scenario_name)
    _manufacturer_charts(mfr_df, events, out_dir, scenario_name)
    _retailer_charts(retailer_df, run_df, events, out_dir, scenario_name)

    print(f"Charts saved to {out_dir}/")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
        if data_dir.is_dir():
            generate_charts(data_dir.name, data_dir)
        else:
            print(f"Error: {data_dir} is not a directory.")
    else:
        run_csv_path = Path("logs/run.csv")
        if run_csv_path.exists():
            for s in pd.read_csv(run_csv_path)["scenario"].unique():
                generate_charts(s)
        else:
            print("Error: logs/run.csv not found. Pass a directory path to visualize archived databases.")
