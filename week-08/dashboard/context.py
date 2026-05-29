import csv
import json
from pathlib import Path

_EMPTY = {"scenario": None, "day_total": None, "latest": None, "fill_rate_series": []}


def _day_total(scenarios_dir: Path, scenario: str) -> int | None:
    f = Path(scenarios_dir) / f"{scenario}.json"
    if not f.exists():
        return None
    try:
        events = json.loads(f.read_text()).get("events", [])
        return max((int(e["end_day"]) for e in events), default=None)
    except (ValueError, KeyError):
        return None


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
    latest = {
        "events": last.get("events", ""),
        "demand_mod": float(last["demand_mod"]),
        "supply_mod": float(last["supply_mod"]),
        "lead_mod": float(last["lead_mod"]),
        "fill_rate": float(last["fill_rate_pct"]),
        "backordered": int(last["backordered"]),
        "day": int(last["day"]),
    }
    return {"scenario": scenario, "day_total": _day_total(scenarios_dir, scenario),
            "latest": latest, "fill_rate_series": series}
