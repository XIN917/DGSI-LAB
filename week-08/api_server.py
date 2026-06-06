#!/usr/bin/env python3
"""FastAPI service that wraps turn_engine for frontend integration."""
import csv
import json
import queue
import threading
import time
import uuid
from pathlib import Path

try:
    import httpx
except ImportError:
    raise SystemExit("httpx missing. Run: pip install httpx")

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, StreamingResponse
    from pydantic import BaseModel
except ImportError:
    raise SystemExit("fastapi/pydantic missing. Run: pip install fastapi uvicorn")

import turn_engine

ROOT = Path(__file__).parent

app = FastAPI(title="DGSI Turn Engine API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Run registry ──────────────────────────────────────────────────────────────
# In-memory for the current session; completed runs are persisted to logs/runs.json
# so elapsed time is visible after restarts. Only completed/cancelled/error runs
# are restored — no ghost "running" entries with missing live data.

_runs: dict[str, dict] = {}
_runs_lock = threading.Lock()
_RUNS_FILE = ROOT / "logs" / "runs.json"
_PERSIST_KEYS = ("id", "status", "scenario", "days", "start_day", "model", "started_at", "elapsed_seconds", "error")


def _persist_runs():
    """Persist all known runs to disk so they survive a server restart."""
    _RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        run_id: {k: run[k] for k in _PERSIST_KEYS if k in run}
        for run_id, run in _runs.items()
    }
    _RUNS_FILE.write_text(json.dumps(snapshot, indent=2))


def _load_runs():
    """Restore run history from logs/runs.json on server start."""
    if not _RUNS_FILE.exists():
        return
    try:
        data = json.loads(_RUNS_FILE.read_text())
        for run_id, meta in data.items():
            _runs[run_id] = {**meta, "queue": queue.Queue(), "thread": None, "result": None}
    except Exception:
        pass


_load_runs()

SUPPORTED_MODELS = [
    {"id": "gemini-3.1-flash-lite", "label": "Gemini 3.1 Flash Lite", "provider": "google", "default": True},
    {"id": "gemma-4-26b-a4b-it",    "label": "Gemma 4 26B",           "provider": "google", "default": False},
    {"id": "gemini-2.5-flash",      "label": "Gemini 2.5 Flash",      "provider": "google", "default": False},
    {"id": "gemini-2.5-pro",        "label": "Gemini 2.5 Pro",        "provider": "google", "default": False},
    {"id": "gemini-2.0-flash",      "label": "Gemini 2.0 Flash",      "provider": "google", "default": False},
    {"id": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5",  "provider": "anthropic", "default": False},
    {"id": "claude-sonnet-4-6",     "label": "Claude Sonnet 4.6",     "provider": "anthropic", "default": False},
    {"id": "claude-opus-4-7",       "label": "Claude Opus 4.7",       "provider": "anthropic", "default": False},
]


def _get_run(run_id: str) -> dict:
    with _runs_lock:
        run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


# ── Background simulation thread ──────────────────────────────────────────────

def _simulation_worker(run_id: str, kwargs: dict):
    run = _runs[run_id]
    q: queue.Queue = run["queue"]

    def progress(msg: str):
        q.put(msg)
        print(f"[{run_id[:8]}] {msg}")

    def is_cancelled():
        return _runs.get(run_id, {}).get("status") == "cancelled"

    try:
        result = turn_engine.run_simulation(progress_cb=progress, cancel_check=is_cancelled, **kwargs)
        with _runs_lock:
            if run["status"] != "cancelled":
                run["status"] = "done"
            run["result"] = result
            run["elapsed_seconds"] = round(time.time() - run["started_at"], 1)
            _persist_runs()
    except Exception as exc:
        with _runs_lock:
            run["status"] = "error"
            run["error"] = str(exc)
            run["elapsed_seconds"] = round(time.time() - run["started_at"], 1)
            _persist_runs()
        q.put(f"ERROR {exc}")
    finally:
        q.put(None)  # sentinel — stream ends


# ── Request / response models ─────────────────────────────────────────────────

class StartRunRequest(BaseModel):
    scenario: str = "calm-market"
    days: int = 15
    start_day: int = 1
    model: str = "gemini-3.1-flash-lite"
    config: str = "config/sim.json"
    verbose: bool = False
    full_skill_prompt: bool = False


# ── Simulation control ────────────────────────────────────────────────────────

@app.post("/run", status_code=201)
def start_run(body: StartRunRequest):
    """Start a new simulation run. Returns run_id immediately."""
    scenario_path = ROOT / "scenarios" / f"{body.scenario}.json"
    if not scenario_path.exists():
        raise HTTPException(status_code=422, detail=f"Scenario '{body.scenario}' not found")

    config_path = ROOT / body.config
    if not config_path.exists():
        raise HTTPException(status_code=422, detail=f"Config '{body.config}' not found")

    if body.days < 1 or body.start_day < 1 or body.start_day > body.days:
        raise HTTPException(status_code=422, detail="Invalid days / start_day combination")

    with _runs_lock:
        active = next((r for r in _runs.values() if r["status"] == "running"), None)
    if active:
        raise HTTPException(
            status_code=409,
            detail=f"Run {active['id'][:8]} is already running ({active['scenario']}). Stop it before starting a new one."
        )

    run_id = str(uuid.uuid4())
    q: queue.Queue = queue.Queue()

    with _runs_lock:
        _runs[run_id] = {
            "id": run_id,
            "status": "running",
            "scenario": body.scenario,
            "days": body.days,
            "start_day": body.start_day,
            "model": body.model,
            "started_at": time.time(),
            "queue": q,
            "result": None,
            "error": None,
        }

    kwargs = {
        "config_json": str(config_path),
        "scenario_json": str(scenario_path),
        "days": body.days,
        "start_day": body.start_day,
        "model": body.model,
        "verbose": body.verbose,
        "full_skill_prompt": body.full_skill_prompt,
    }
    thread = threading.Thread(target=_simulation_worker, args=(run_id, kwargs), daemon=True)
    thread.start()

    with _runs_lock:
        _runs[run_id]["thread"] = thread
        _persist_runs()

    return {"run_id": run_id}


@app.delete("/run/{run_id}")
def cancel_run(run_id: str):
    """Cancel a running simulation (best-effort — stops after current day)."""
    run = _get_run(run_id)
    if run["status"] != "running":
        raise HTTPException(status_code=409, detail=f"Run is already {run['status']}")
    with _runs_lock:
        _runs[run_id]["status"] = "cancelled"
        _persist_runs()
    return {"run_id": run_id, "status": "cancelled"}


@app.get("/run/{run_id}/stream")
def stream_run(run_id: str):
    """SSE stream of log lines for a running (or recently finished) simulation."""
    run = _get_run(run_id)
    q: queue.Queue = run["queue"]

    def generate():
        while True:
            try:
                line = q.get(timeout=60)
            except queue.Empty:
                yield "data: KEEPALIVE\n\n"
                continue
            if line is None:
                yield "data: STREAM_END\n\n"
                break
            yield f"data: {line}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/run/{run_id}/status")
def run_status(run_id: str):
    """Current status and progress of a run."""
    run = _get_run(run_id)
    elapsed = round(time.time() - run["started_at"], 1)
    resp = {
        "run_id": run_id,
        "status": run["status"],
        "scenario": run["scenario"],
        "days": run["days"],
        "model": run["model"],
        "elapsed_seconds": elapsed,
        "error": run.get("error"),
    }
    if run.get("result"):
        resp["result"] = run["result"]
    return resp


@app.delete("/runs")
def delete_runs(ids: str = ""):
    """Remove finished/errored runs from registry. Pass ?ids=id1,id2 for specific runs, or omit for all non-running."""
    target_ids = [i.strip() for i in ids.split(",") if i.strip()] if ids else None
    removed = []
    with _runs_lock:
        to_remove = [
            rid for rid, r in _runs.items()
            if r["status"] != "running" and (target_ids is None or rid in target_ids)
        ]
        for rid in to_remove:
            del _runs[rid]
            removed.append(rid)
        _persist_runs()
    return {"removed": removed}


@app.get("/runs")
def list_runs():
    """List all runs (active and historical) in this server session."""
    with _runs_lock:
        return [
            {
                "run_id": r["id"],
                "status": r["status"],
                "scenario": r["scenario"],
                "days": r["days"],
                "start_day": r.get("start_day", 1),
                "model": r["model"],
                "elapsed_seconds": r["elapsed_seconds"] if r["status"] in ("done", "cancelled", "error") else round(time.time() - r["started_at"], 1),
            }
            for r in _runs.values()
        ]


# ── Scenario / config discovery ───────────────────────────────────────────────

@app.get("/scenarios")
def list_scenarios():
    """List all available scenario JSON files."""
    return [
        {"name": p.stem, "path": str(p.relative_to(ROOT))}
        for p in sorted((ROOT / "scenarios").glob("*.json"))
    ]


@app.get("/scenarios/{name}")
def get_scenario(name: str):
    """Return the full content of a scenario file."""
    path = ROOT / "scenarios" / f"{name}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Scenario '{name}' not found")
    return json.loads(path.read_text())


@app.get("/models")
def list_models():
    """List supported model identifiers."""
    return SUPPORTED_MODELS


# ── Run data ──────────────────────────────────────────────────────────────────

@app.get("/run/{run_id}/logs")
def get_logs(run_id: str, page: int = 1, page_size: int = 100):
    """Return paginated agent log lines from the day log files for this run."""
    run = _get_run(run_id)
    log_dir = ROOT / "logs" / run["scenario"]
    if not log_dir.exists():
        return {"run_id": run_id, "lines": [], "total": 0}

    all_lines: list[str] = []
    for log_file in sorted(log_dir.glob("day-*.log")):
        all_lines.extend(log_file.read_text(errors="replace").splitlines())

    start = (page - 1) * page_size
    return {
        "run_id": run_id,
        "page": page,
        "page_size": page_size,
        "total": len(all_lines),
        "lines": all_lines[start: start + page_size],
    }


@app.get("/run/{run_id}/kpis")
def get_kpis(run_id: str):
    """Return daily KPI rows for this run from logs/{scenario}/run.csv."""
    run = _get_run(run_id)
    csv_path = ROOT / "logs" / run["scenario"] / "run.csv"
    if not csv_path.exists():
        return []
    with csv_path.open() as f:
        rows = list(csv.DictReader(f))
    return rows


@app.get("/run/{run_id}/inventory")
def get_inventory(run_id: str):
    """Return inventory-over-time data from the archived SQLite databases."""
    run = _get_run(run_id)
    db_dir = ROOT / "logs" / run["scenario"]
    data = {}
    for svc in ("provider", "manufacturer", "retailer"):
        db_path = db_dir / f"{svc}.db"
        if not db_path.exists():
            continue
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT sim_day, product, quantity FROM metrics WHERE metric_type='inventory' ORDER BY sim_day"
            )
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            data[svc] = rows
        except Exception as exc:
            data[svc] = {"error": str(exc)}
    return data


@app.get("/run/{run_id}/prices")
def get_prices(run_id: str):
    """Return price history from the archived SQLite databases."""
    run = _get_run(run_id)
    db_dir = ROOT / "logs" / run["scenario"]
    data = {}
    for svc in ("provider", "manufacturer", "retailer"):
        db_path = db_dir / f"{svc}.db"
        if not db_path.exists():
            continue
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT sim_day, product, price FROM metrics WHERE metric_type='price' ORDER BY sim_day"
            )
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            data[svc] = rows
        except Exception as exc:
            data[svc] = {"error": str(exc)}
    return data


@app.get("/run/{run_id}/charts")
def list_charts(run_id: str):
    """List generated chart PNG files for this run."""
    run = _get_run(run_id)
    chart_dir = ROOT / "logs" / run["scenario"] / "charts"
    if not chart_dir.exists():
        return []
    return [
        {"name": p.name, "path": f"/run/{run_id}/charts/{p.name}"}
        for p in sorted(chart_dir.glob("*.png"))
    ]


@app.get("/run/{run_id}/charts/{filename}")
def get_chart(run_id: str, filename: str):
    """Serve a chart PNG file."""
    run = _get_run(run_id)
    chart_path = ROOT / "logs" / run["scenario"] / "charts" / filename
    if not chart_path.exists():
        raise HTTPException(status_code=404, detail="Chart not found")
    return FileResponse(str(chart_path), media_type="image/png")


# ── Reset ─────────────────────────────────────────────────────────────────────

_reset_state: dict = {"status": "idle", "output": ""}

@app.post("/reset")
def reset_services():
    """Start reset_all.sh in background. Returns immediately; poll GET /reset/status."""
    import subprocess
    if _reset_state.get("status") == "running":
        return {"ok": False, "status": "running", "output": "Reset already in progress."}
    script = ROOT / "scripts" / "reset_all.sh"

    def _run():
        _reset_state["status"] = "running"
        _reset_state["output"] = ""
        result = subprocess.run([str(script)], capture_output=True, text=True)
        _reset_state["output"] = result.stdout + result.stderr
        _reset_state["status"] = "done" if result.returncode == 0 else "error"

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "status": "running"}


@app.get("/reset/status")
def reset_status():
    """Poll reset progress."""
    return _reset_state


# ── Service health ────────────────────────────────────────────────────────────

@app.get("/services/status")
def services_status():
    """Check whether provider, manufacturer, and retailer HTTP services are up."""
    config_path = ROOT / "config" / "sim.json"
    if not config_path.exists():
        raise HTTPException(status_code=500, detail="sim.json not found")

    cfg = json.loads(config_path.read_text())
    checks = {}

    urls = {
        "provider": cfg["providers"][0]["url"],
        "manufacturer": cfg["manufacturer"]["url"],
        "retailer": cfg["retailers"][0]["url"],
    }
    for name, url in urls.items():
        try:
            r = httpx.get(f"{url}/api/day/current", timeout=3)
            checks[name] = {"url": url, "up": r.status_code < 500, "status_code": r.status_code}
        except Exception as exc:
            checks[name] = {"url": url, "up": False, "error": str(exc)}

    return checks


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
