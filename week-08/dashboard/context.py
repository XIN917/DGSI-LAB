import csv
import json
from pathlib import Path

_EMPTY = {"scenario": None, "day_total": None, "latest": None, "fill_rate_series": []}


def _load_scenario_events(scenarios_dir: Path, scenario: str) -> list[dict]:
    f = Path(scenarios_dir) / f"{scenario}.json"
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text()).get("events", [])
    except (ValueError, KeyError):
        return []


def _day_total(scenarios_dir: Path, scenario: str) -> int | None:
    events = _load_scenario_events(scenarios_dir, scenario)
    return max((int(e["end_day"]) for e in events), default=None) if events else None


def load_context(run_csv: Path, scenarios_dir: Path) -> dict:
    run_csv = Path(run_csv)
    if not run_csv.exists():
        return dict(_EMPTY)
    with run_csv.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return dict(_EMPTY)
    scenario = rows[-1]["scenario"]
    scenario_rows = [r for r in rows if r["scenario"] == scenario]
    last = scenario_rows[-1]
    series = [[int(r["day"]), float(r["fill_rate_pct"])] for r in scenario_rows]
    total_backordered = sum(int(r["backordered"]) for r in scenario_rows)
    total_orders = sum(int(r["orders_placed"]) for r in scenario_rows)
    total_fulfilled = sum(int(r["fulfilled"]) for r in scenario_rows)
    avg_fill_rate = round(total_fulfilled / total_orders * 100, 1) if total_orders else None
    latest = {
        "events": last.get("events", ""),
        "demand_mod": float(last["demand_mod"]),
        "supply_mod": float(last["supply_mod"]),
        "lead_mod": float(last["lead_mod"]),
        "fill_rate": float(last["fill_rate_pct"]),
        "backordered": int(last["backordered"]),
        "day": int(last["day"]),
    }
    raw_events = _load_scenario_events(scenarios_dir, scenario)
    event_summary = [
        {"name": e["name"], "start_day": e["start_day"], "end_day": e["end_day"],
         "demand_mod": e.get("demand_modifier", 1.0), "supply_mod": e.get("supply_modifier", 1.0)}
        for e in raw_events if e.get("name", "normal") != "normal"
    ]
    return {"scenario": scenario, "day_total": _day_total(scenarios_dir, scenario),
            "latest": latest, "fill_rate_series": series,
            "total_backordered": total_backordered, "avg_fill_rate": avg_fill_rate,
            "event_summary": event_summary}
