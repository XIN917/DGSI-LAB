"""Tests for api_server.py — uses FastAPI TestClient, no live services required."""
import json
import queue
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

import api_server
from api_server import app, _runs, _runs_lock, _reset_state

ROOT = Path(__file__).parent.parent
client = TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def clean_runs():
    """Isolate each test: clear in-memory run registry and reset state."""
    with _runs_lock:
        _runs.clear()
    _reset_state["status"] = "idle"
    _reset_state["output"] = ""
    yield
    with _runs_lock:
        _runs.clear()


# ── /scenarios ────────────────────────────────────────────────────────────────

def test_list_scenarios():
    r = client.get("/scenarios")
    assert r.status_code == 200
    names = [s["name"] for s in r.json()]
    assert "calm-market" in names
    assert "holiday-rush" in names


def test_get_scenario_valid():
    r = client.get("/scenarios/calm-market")
    assert r.status_code == 200
    body = r.json()
    assert "events" in body
    assert "scenario_name" in body


def test_get_scenario_not_found():
    r = client.get("/scenarios/nonexistent")
    assert r.status_code == 404


# ── /models ───────────────────────────────────────────────────────────────────

def test_list_models():
    r = client.get("/models")
    assert r.status_code == 200
    models = r.json()
    assert any(m["default"] for m in models), "exactly one model should be default"
    ids = [m["id"] for m in models]
    assert "gemini-3.1-flash-lite" in ids


# ── /run (POST) ───────────────────────────────────────────────────────────────

def _fake_worker(run_id, kwargs):
    """Inject a synthetic worker that completes immediately without calling turn_engine."""
    run = _runs[run_id]
    time.sleep(0.05)
    with _runs_lock:
        run["status"] = "done"
        run["result"] = {"days_run": kwargs.get("days", 1)}
        run["elapsed_seconds"] = 0.1
    run["queue"].put("day 1 done")
    run["queue"].put(None)


def test_start_run_returns_run_id(monkeypatch):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    r = client.post("/run", json={"scenario": "calm-market", "days": 1})
    assert r.status_code == 201
    assert "run_id" in r.json()


def test_start_run_invalid_scenario():
    r = client.post("/run", json={"scenario": "does-not-exist", "days": 1})
    assert r.status_code == 422


def test_start_run_invalid_days():
    r = client.post("/run", json={"scenario": "calm-market", "days": 0})
    assert r.status_code == 422


def test_start_run_start_day_exceeds_days():
    r = client.post("/run", json={"scenario": "calm-market", "days": 5, "start_day": 10})
    assert r.status_code == 422


def test_start_run_conflict_when_already_running(monkeypatch):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    r1 = client.post("/run", json={"scenario": "calm-market", "days": 1})
    assert r1.status_code == 201
    run_id = r1.json()["run_id"]

    # Force the run back to "running" so the conflict check triggers
    with _runs_lock:
        _runs[run_id]["status"] = "running"

    r2 = client.post("/run", json={"scenario": "calm-market", "days": 1})
    assert r2.status_code == 409


# ── /run/{id}/status ──────────────────────────────────────────────────────────

def test_run_status_not_found():
    r = client.get("/run/00000000-0000-0000-0000-000000000000/status")
    assert r.status_code == 404


def test_run_status_fields(monkeypatch):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    run_id = client.post("/run", json={"scenario": "calm-market", "days": 2}).json()["run_id"]
    r = client.get(f"/run/{run_id}/status")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == run_id
    assert body["scenario"] == "calm-market"
    assert body["days"] == 2
    assert "status" in body
    assert "elapsed_seconds" in body


# ── /run/{id} (DELETE / cancel) ───────────────────────────────────────────────

def test_cancel_run(monkeypatch):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    run_id = client.post("/run", json={"scenario": "calm-market", "days": 1}).json()["run_id"]
    with _runs_lock:
        _runs[run_id]["status"] = "running"
    r = client.delete(f"/run/{run_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_cancel_already_done_run(monkeypatch):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    run_id = client.post("/run", json={"scenario": "calm-market", "days": 1}).json()["run_id"]
    # wait for fake worker to finish
    time.sleep(0.2)
    r = client.delete(f"/run/{run_id}")
    assert r.status_code == 409


def test_cancel_not_found():
    r = client.delete("/run/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# ── /runs (GET / DELETE) ──────────────────────────────────────────────────────

def test_list_runs_empty():
    r = client.get("/runs")
    assert r.status_code == 200
    assert r.json() == []


def test_list_runs_after_start(monkeypatch):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    client.post("/run", json={"scenario": "calm-market", "days": 1})
    r = client.get("/runs")
    assert len(r.json()) == 1
    assert r.json()[0]["scenario"] == "calm-market"


def test_delete_runs_removes_finished(monkeypatch):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    run_id = client.post("/run", json={"scenario": "calm-market", "days": 1}).json()["run_id"]
    time.sleep(0.2)
    r = client.delete("/runs")
    assert r.status_code == 200
    removed = r.json()["removed"]
    assert run_id in removed
    assert client.get("/runs").json() == []


def test_delete_runs_does_not_remove_running(monkeypatch):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    run_id = client.post("/run", json={"scenario": "calm-market", "days": 1}).json()["run_id"]
    with _runs_lock:
        _runs[run_id]["status"] = "running"
    r = client.delete("/runs")
    assert run_id not in r.json()["removed"]
    assert len(client.get("/runs").json()) == 1


# ── /run/{id}/logs ────────────────────────────────────────────────────────────

def test_get_logs_no_log_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    run_id = client.post("/run", json={"scenario": "calm-market", "days": 1}).json()["run_id"]
    # Point ROOT at a tmp dir with no logs/ subdirectory
    monkeypatch.setattr(api_server, "ROOT", tmp_path)
    r = client.get(f"/run/{run_id}/logs")
    assert r.status_code == 200
    assert r.json()["lines"] == []
    assert r.json()["total"] == 0


def test_get_logs_pagination(monkeypatch, tmp_path):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    run_id = client.post("/run", json={"scenario": "calm-market", "days": 1}).json()["run_id"]

    log_dir = tmp_path / "logs" / "calm-market"
    log_dir.mkdir(parents=True)
    (log_dir / "day-001.log").write_text("\n".join(f"line {i}" for i in range(50)))
    (log_dir / "day-002.log").write_text("\n".join(f"line {i}" for i in range(50, 120)))

    monkeypatch.setattr(api_server, "ROOT", tmp_path)
    r = client.get(f"/run/{run_id}/logs?page=1&page_size=30")
    body = r.json()
    assert body["total"] == 120
    assert len(body["lines"]) == 30
    assert body["lines"][0] == "line 0"

    r2 = client.get(f"/run/{run_id}/logs?page=2&page_size=30")
    assert r2.json()["lines"][0] == "line 30"


# ── /run/{id}/kpis ────────────────────────────────────────────────────────────

def test_get_kpis_no_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    run_id = client.post("/run", json={"scenario": "calm-market", "days": 1}).json()["run_id"]
    monkeypatch.setattr(api_server, "ROOT", tmp_path)
    r = client.get(f"/run/{run_id}/kpis")
    assert r.status_code == 200
    assert r.json() == []


def test_get_kpis_with_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    run_id = client.post("/run", json={"scenario": "calm-market", "days": 1}).json()["run_id"]

    csv_dir = tmp_path / "logs" / "calm-market"
    csv_dir.mkdir(parents=True)
    (csv_dir / "run.csv").write_text("day,retail_fulfilled\n1,10\n2,15\n")

    monkeypatch.setattr(api_server, "ROOT", tmp_path)
    r = client.get(f"/run/{run_id}/kpis")
    rows = r.json()
    assert len(rows) == 2
    assert rows[0]["day"] == "1"
    assert rows[1]["retail_fulfilled"] == "15"


# ── /run/{id}/charts ──────────────────────────────────────────────────────────

def test_list_charts_no_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    run_id = client.post("/run", json={"scenario": "calm-market", "days": 1}).json()["run_id"]
    monkeypatch.setattr(api_server, "ROOT", tmp_path)
    r = client.get(f"/run/{run_id}/charts")
    assert r.status_code == 200
    assert r.json() == []


def test_list_charts_with_pngs(monkeypatch, tmp_path):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    run_id = client.post("/run", json={"scenario": "calm-market", "days": 1}).json()["run_id"]

    chart_dir = tmp_path / "logs" / "calm-market" / "charts"
    chart_dir.mkdir(parents=True)
    (chart_dir / "provider_stock.png").write_bytes(b"\x89PNG")
    (chart_dir / "retailer_prices.png").write_bytes(b"\x89PNG")

    monkeypatch.setattr(api_server, "ROOT", tmp_path)
    r = client.get(f"/run/{run_id}/charts")
    names = [c["name"] for c in r.json()]
    assert "provider_stock.png" in names
    assert "retailer_prices.png" in names


def test_get_chart_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(api_server, "_simulation_worker", _fake_worker)
    run_id = client.post("/run", json={"scenario": "calm-market", "days": 1}).json()["run_id"]
    monkeypatch.setattr(api_server, "ROOT", tmp_path)
    r = client.get(f"/run/{run_id}/charts/missing.png")
    assert r.status_code == 404


# ── /reset ────────────────────────────────────────────────────────────────────

def test_reset_status_idle():
    r = client.get("/reset/status")
    assert r.status_code == 200
    assert r.json()["status"] == "idle"


def test_reset_blocks_second_call(monkeypatch):
    _reset_state["status"] = "running"
    r = client.post("/reset")
    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert r.json()["status"] == "running"


def test_reset_fires_and_completes(monkeypatch, tmp_path):
    # Provide a fake reset script that exits 0 quickly
    script = tmp_path / "scripts" / "reset_all.sh"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\necho 'reset ok'\n")
    script.chmod(0o755)
    monkeypatch.setattr(api_server, "ROOT", tmp_path)

    r = client.post("/reset")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # Poll until done (background thread)
    for _ in range(20):
        time.sleep(0.1)
        st = client.get("/reset/status").json()
        if st["status"] != "running":
            break
    assert st["status"] == "done"
    assert "reset ok" in st["output"]


def test_reset_reports_error_on_script_failure(monkeypatch, tmp_path):
    script = tmp_path / "scripts" / "reset_all.sh"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\necho 'boom' >&2\nexit 1\n")
    script.chmod(0o755)
    monkeypatch.setattr(api_server, "ROOT", tmp_path)

    _reset_state["status"] = "idle"
    client.post("/reset")

    for _ in range(20):
        time.sleep(0.1)
        st = client.get("/reset/status").json()
        if st["status"] != "running":
            break
    assert st["status"] == "error"
    assert "boom" in st["output"]
