#!/usr/bin/env python3
"""Generate Week 8 metrics charts from service SQLite databases."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

_TEMP_BASE = Path(tempfile.gettempdir()) / "week8-analysis"
_MPLCONFIGDIR = _TEMP_BASE / "matplotlib"
_XDG_CACHE_HOME = _TEMP_BASE / "cache"
_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
_XDG_CACHE_HOME.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("MPLCONFIGDIR", str(_MPLCONFIGDIR))
os.environ.setdefault("XDG_CACHE_HOME", str(_XDG_CACHE_HOME))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DBS = {
    "provider": ROOT / "provider" / "data" / "provider.db",
    "manufacturer": ROOT / "manufacturer" / "data" / "simulation.db",
    "retailer": ROOT / "retailer" / "data" / "retailer.db",
}


def read_metrics(db_path: Path) -> list[dict]:
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT sim_day, metric, entity, value FROM metrics_snapshots ORDER BY sim_day"
            ).fetchall()
        except sqlite3.OperationalError:
            return []
    return [dict(row) for row in rows]


def plot_metric(rows: list[dict], metric_suffix: str, title: str, output: Path) -> None:
    subset = [row for row in rows if row["metric"].endswith(metric_suffix)]
    if not subset:
        return
    plt.figure(figsize=(10, 5))
    for entity in sorted({row["entity"] for row in subset}):
        series = [row for row in subset if row["entity"] == entity]
        plt.plot([row["sim_day"] for row in series], [row["value"] for row in series], marker="o", label=entity)
    plt.title(title)
    plt.xlabel("Simulation day")
    plt.ylabel("Value")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output)
    plt.close()


def plot_scenario_events(scenario: dict, output: Path) -> None:
    plt.figure(figsize=(10, 3))
    for idx, event in enumerate(scenario.get("events", []), start=1):
        start = int(event.get("start_day", event.get("day", 1)))
        end = int(event.get("end_day", start))
        plt.barh([idx], [end - start + 1], left=[start], label=event["name"])
    plt.title("Scenario event overlay")
    plt.xlabel("Simulation day")
    plt.yticks([])
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(output)
    plt.close()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python analysis/generate_charts.py scenarios/holiday-rush.json", file=sys.stderr)
        return 2

    scenario_path = Path(argv[1])
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    name = scenario.get("name", scenario_path.stem)
    output_dir = ROOT / "analysis" / "output" / name
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for service, db_path in DBS.items():
        for row in read_metrics(db_path):
            row["service"] = service
            rows.append(row)

    charts = {
        "inventory.png": ("_stock", "Inventory over time"),
        "prices.png": ("_price", "Prices over time"),
        "orders.png": ("_orders", "Orders by status"),
    }
    for filename, (metric_prefix, title) in charts.items():
        plot_metric(rows, metric_prefix, title, output_dir / filename)
    plot_scenario_events(scenario, output_dir / "scenario-events.png")

    summary = [
        f"# {name} Summary",
        "",
        "## Charts",
        "",
        "- [Inventory over time](inventory.png)",
        "- [Prices over time](prices.png)",
        "- [Customer and supply-chain orders](orders.png)",
        "- [Scenario event overlay](scenario-events.png)",
        "",
        "## Interpretation Prompts",
        "",
        "- Which event windows correspond to stockouts or backorder growth?",
        "- Did price changes dampen demand or simply lag shortages?",
        "- Did upstream recovery happen before or after retail service levels improved?",
    ]
    (output_dir / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
