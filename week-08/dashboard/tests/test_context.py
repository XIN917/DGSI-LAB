import json
from dashboard.context import load_context

RUN_CSV = (
    "scenario,day,demand_mod,supply_mod,lead_mod,price_sensitivity,events,orders_placed,fulfilled,backordered,stockout,fill_rate_pct\n"
    "holiday-rush,13,1.0,1.0,1.0,1.0,Black Friday,10,9,1,0,90.0\n"
    "holiday-rush,14,2.0,0.5,1.0,1.0,Black Friday + chip shortage,12,8,4,0,66.7\n"
)


def test_load_context_reads_latest_row_and_series(tmp_path):
    run_csv = tmp_path / "run.csv"
    run_csv.write_text(RUN_CSV)
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    (scenarios / "holiday-rush.json").write_text(json.dumps({
        "events": [{"start_day": 1, "end_day": 25, "demand_modifier": 1.0, "supply_modifier": 1.0}]}))

    ctx = load_context(run_csv=run_csv, scenarios_dir=scenarios)

    assert ctx["scenario"] == "holiday-rush"
    assert ctx["day_total"] == 25
    assert ctx["latest"]["fill_rate"] == 66.7
    assert ctx["latest"]["backordered"] == 4
    assert ctx["latest"]["demand_mod"] == 2.0
    assert ctx["latest"]["events"] == "Black Friday + chip shortage"
    assert ctx["fill_rate_series"] == [[13, 90.0], [14, 66.7]]


def test_load_context_missing_file_is_graceful(tmp_path):
    ctx = load_context(run_csv=tmp_path / "nope.csv", scenarios_dir=tmp_path)
    assert ctx == {"scenario": None, "day_total": None, "latest": None, "fill_rate_series": []}
