"""Integration tests for the turn engine.

These tests exercise turn_engine.Engine end-to-end against an in-process
`httpx.MockTransport` that emulates the three downstream services. They
verify the engine's REST contract and the fallback orchestration, without
needing real subprocesses or a network.

What they cover (cross-referenced with the recent fix commits):

- A1 — `fallback_manufacturer` maps each raw material to the correct
  provider product_id via the cached catalog, instead of hardcoding id=1.
- A3 — `manufacturer_token()` refuses to silently fall back to demo
  credentials when `manufacturer_auth` is missing from config.
- M1 — A transient HTTP failure on day N does not abort the remaining
  days; the engine logs the error and continues with day N+1.
- General — Each day calls `/api/day/advance` and `/api/metrics/snapshot`
  on all three services after the agents run.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import httpx
import pytest

from turn_engine import Engine


def _base_config(tmp_path: Path) -> dict:
    """Sim config wired to the mock services' base URLs.

    The hostnames are fake — MockTransport dispatches by URL not by DNS,
    so we just need stable values to key the per-service handlers.
    """
    return {
        "services": {
            "provider": "http://mock-provider",
            "manufacturer": "http://mock-manufacturer",
            "retailer": "http://mock-retailer",
        },
        "claude_path": "/nonexistent/claude",
        "claude_timeout_seconds": 5,
        "fallback_mode": "always",
        "manufacturer_auth": {"username": "test", "password": "test"},
        "demand": {
            "P3D-Classic": {"base_daily_units": 0, "reference_price": 1500.0},
            "P3D-Pro": {"base_daily_units": 0, "reference_price": 2500.0},
        },
        "fallback": {
            "retailer_reorder_threshold": 6,
            "retailer_reorder_quantity": 12,
            "manufacturer_raw_threshold": 80,
            "manufacturer_restock_quantity": 120,
            "provider_restock_quantity": 150,
        },
    }


def _calm_scenario() -> dict:
    return {
        "name": "test-calm",
        "events": [
            {
                "name": "steady",
                "start_day": 1,
                "end_day": 5,
                "demand_modifier": 1.0,
                "supply_modifier": 1.0,
                "lead_time_modifier": 1.0,
                "price_sensitivity": 1.0,
            }
        ],
    }


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _build_engine(tmp_path: Path, config: dict, scenario: dict, days: int) -> Engine:
    cfg_path = _write_json(tmp_path / "sim.json", config)
    scn_path = _write_json(tmp_path / "scenario.json", scenario)
    return Engine(str(cfg_path), str(scn_path), days)


class _MockServices:
    """Tracks every request the engine makes and serves canned responses.

    Construct with a per-service handler dict. Each handler is
    `(method, path) -> (status, json_body)`. Unmatched routes return 404
    so the test fails loudly if the engine starts calling unexpected
    endpoints.
    """

    def __init__(
        self,
        provider_handler: Callable[[httpx.Request], httpx.Response] | None = None,
        manufacturer_handler: Callable[[httpx.Request], httpx.Response] | None = None,
        retailer_handler: Callable[[httpx.Request], httpx.Response] | None = None,
    ):
        self.requests: list[tuple[str, str, str]] = []  # (method, host, path)
        self._handlers = {
            "mock-provider": provider_handler or self._default_404,
            "mock-manufacturer": manufacturer_handler or self._default_404,
            "mock-retailer": retailer_handler or self._default_404,
        }

    @staticmethod
    def _default_404(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": f"no handler for {request.url}"})

    def transport(self) -> httpx.MockTransport:
        def dispatch(request: httpx.Request) -> httpx.Response:
            host = request.url.host
            self.requests.append((request.method, host, request.url.path))
            handler = self._handlers.get(host, self._default_404)
            return handler(request)

        return httpx.MockTransport(dispatch)

    def calls_to(self, host: str) -> list[tuple[str, str]]:
        return [(m, p) for (m, h, p) in self.requests if h == host]


# ---------------------------------------------------------------------------
# A3 — manufacturer_token must not silently use demo credentials
# ---------------------------------------------------------------------------


def test_manufacturer_token_raises_when_auth_missing(tmp_path):
    config = _base_config(tmp_path)
    del config["manufacturer_auth"]
    engine = _build_engine(tmp_path, config, _calm_scenario(), days=1)

    with pytest.raises(KeyError, match="manufacturer_auth"):
        engine.manufacturer_token()


# ---------------------------------------------------------------------------
# A1 — fallback_manufacturer maps material name → correct provider product_id
# ---------------------------------------------------------------------------


def test_fallback_manufacturer_uses_catalog_mapped_product_id(tmp_path):
    """The manufacturer reports low stock of `pcb_control`. The engine
    must restock provider product whose `name` matches `pcb_control`,
    not the hardcoded `product_id=1`.
    """
    provider_catalog = [
        {"id": 7, "name": "Frame Kit", "lead_time_days": 2},
        {"id": 11, "name": "PCB Control", "lead_time_days": 3},
        {"id": 13, "name": "Motor Assembly", "lead_time_days": 2},
    ]
    restocked: list[tuple[int, dict]] = []

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/catalog/":
            return httpx.Response(200, json=provider_catalog)
        if request.url.path.startswith("/api/stock/restock/"):
            pid = int(request.url.path.rsplit("/", 1)[-1])
            restocked.append((pid, json.loads(request.content)))
            return httpx.Response(200, json={"product_id": pid, "quantity": 999})
        if request.url.path == "/api/scenario/effects":
            return httpx.Response(200, json={"ok": True})
        if request.url.path == "/api/stock/":
            return httpx.Response(200, json=[])  # nothing to do for provider fallback
        if request.url.path == "/api/day/advance":
            return httpx.Response(200, json={"day": 1})
        if request.url.path == "/api/metrics/snapshot":
            return httpx.Response(200, json={"snapshotted": True})
        return httpx.Response(404)

    def manufacturer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"access_token": "tok"})
        if request.url.path == "/api/orders":
            return httpx.Response(200, json=[])  # no pending orders to release
        if request.url.path == "/api/inventory":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {"product_name": "pcb_control", "unit_type": "raw", "quantity": 10},
                        {"product_name": "frame_kit", "unit_type": "raw", "quantity": 200},
                    ]
                },
            )
        if request.url.path == "/api/day/advance":
            return httpx.Response(200, json={"day": 1})
        if request.url.path == "/api/metrics/snapshot":
            return httpx.Response(200, json={"snapshotted": True})
        return httpx.Response(404)

    def retailer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/inventory":
            return httpx.Response(200, json=[])  # no skus to reorder
        if request.url.path == "/api/customer-orders/":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/day/advance":
            return httpx.Response(200, json={"day": 1})
        if request.url.path == "/api/metrics/snapshot":
            return httpx.Response(200, json={"snapshotted": True})
        return httpx.Response(404)

    services = _MockServices(provider, manufacturer, retailer)
    engine = _build_engine(tmp_path, _base_config(tmp_path), _calm_scenario(), days=1)
    engine.client = httpx.Client(transport=services.transport(), timeout=5.0)

    engine.run()

    # Only pcb_control was below threshold (10 < 80). It maps to provider id=11.
    assert restocked == [(11, {"quantity": 120})], restocked


# ---------------------------------------------------------------------------
# M1 — engine survives a transient HTTP failure mid-run
# ---------------------------------------------------------------------------


def test_engine_continues_after_transient_day_failure(tmp_path):
    """Day 1 fails (provider /api/scenario/effects 500), day 2 succeeds.

    Without the per-day try/except, the exception from day 1 would
    propagate out of run() and day 2 would never execute. We assert
    that day 2's metrics snapshot was called.
    """
    state = {"day": 0}
    snapshots_seen: list[int] = []

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/scenario/effects":
            state["day"] += 1
            if state["day"] == 1:
                return httpx.Response(500, json={"error": "boom"})
            return httpx.Response(200, json={"ok": True})
        if request.url.path == "/api/catalog/":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/stock/":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/day/advance":
            return httpx.Response(200, json={"day": state["day"]})
        if request.url.path == "/api/metrics/snapshot":
            snapshots_seen.append(state["day"])
            return httpx.Response(200, json={"snapshotted": True})
        return httpx.Response(404)

    def manufacturer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"access_token": "tok"})
        if request.url.path == "/api/orders":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/inventory":
            return httpx.Response(200, json={"items": []})
        if request.url.path == "/api/day/advance":
            return httpx.Response(200, json={"day": state["day"]})
        if request.url.path == "/api/metrics/snapshot":
            return httpx.Response(200, json={"snapshotted": True})
        return httpx.Response(404)

    def retailer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/inventory":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/customer-orders/":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/day/advance":
            return httpx.Response(200, json={"day": state["day"]})
        if request.url.path == "/api/metrics/snapshot":
            return httpx.Response(200, json={"snapshotted": True})
        return httpx.Response(404)

    services = _MockServices(provider, manufacturer, retailer)
    engine = _build_engine(tmp_path, _base_config(tmp_path), _calm_scenario(), days=2)
    engine.client = httpx.Client(transport=services.transport(), timeout=5.0)

    engine.run()  # must NOT raise

    # Day 1 aborted before snapshots; day 2 must have run snapshots.
    # The provider snapshots_seen list records day 2 at least.
    assert 2 in snapshots_seen, snapshots_seen


# ---------------------------------------------------------------------------
# General — modifiers reach the provider unchanged
# ---------------------------------------------------------------------------


def test_apply_hard_effects_forwards_compounded_modifiers(tmp_path):
    """Two overlapping events must compose multiplicatively before being
    sent to the provider via /api/scenario/effects.
    """
    received: list[dict] = []

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/scenario/effects":
            received.append(json.loads(request.content))
            return httpx.Response(200, json={"ok": True})
        if request.url.path == "/api/catalog/":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/stock/":
            return httpx.Response(200, json=[])
        return httpx.Response(200, json={"ok": True})

    def manufacturer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"access_token": "tok"})
        return httpx.Response(200, json={"items": []} if "inventory" in request.url.path else [])

    def retailer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/inventory":
            return httpx.Response(200, json=[])
        return httpx.Response(200, json={"ok": True})

    scenario = {
        "name": "overlap",
        "events": [
            {"start_day": 1, "end_day": 5, "supply_modifier": 0.5, "lead_time_modifier": 2.0},
            {"start_day": 1, "end_day": 5, "supply_modifier": 0.8, "lead_time_modifier": 1.5},
        ],
    }
    services = _MockServices(provider, manufacturer, retailer)
    engine = _build_engine(tmp_path, _base_config(tmp_path), scenario, days=1)
    engine.client = httpx.Client(transport=services.transport(), timeout=5.0)

    engine.run()

    assert len(received) == 1
    assert received[0]["supply_modifier"] == pytest.approx(0.5 * 0.8)
    assert received[0]["lead_time_modifier"] == pytest.approx(2.0 * 1.5)


# ---------------------------------------------------------------------------
# General — every day triggers /api/day/advance and /api/metrics/snapshot
#           on all three services, in that order
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Edge: Claude binary is missing → engine should fall back, not crash
# ---------------------------------------------------------------------------


def test_run_claude_returns_missing_when_binary_does_not_exist(tmp_path):
    """A configured `claude_path` that doesn't exist must return
    'missing' (and the run_role path then triggers fallback). This pins
    the contract that lets the simulation survive on a CI box without
    Claude installed."""
    config = _base_config(tmp_path)
    config["claude_path"] = "/definitely/does/not/exist/claude"
    config["fallback_mode"] = "auto"  # try Claude first, then fallback
    engine = _build_engine(tmp_path, config, _calm_scenario(), days=1)

    class _Sig:
        name = "test"
        modifiers = {"demand_modifier": 1.0}

    assert engine.run_claude(day=1, role="retail", signal=_Sig()) == "missing"


# ---------------------------------------------------------------------------
# Edge: manufacturer auth fails → token() returns None, auth() returns {}
# ---------------------------------------------------------------------------


def test_manufacturer_token_returns_none_when_login_endpoint_fails(tmp_path):
    def manufacturer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(401, json={"detail": "invalid credentials"})
        return httpx.Response(404)

    mocks = _MockServices(manufacturer_handler=manufacturer)
    engine = _build_engine(tmp_path, _base_config(tmp_path), _calm_scenario(), days=1)
    engine.client = httpx.Client(transport=mocks.transport(), timeout=5.0)

    assert engine.manufacturer_token() is None
    # auth() with a None token must produce an empty headers dict, not crash
    assert engine.auth(None) == {}


# ---------------------------------------------------------------------------
# Edge: snapshot endpoint 500s on one service — engine continues to next day
# ---------------------------------------------------------------------------


def test_engine_tolerates_snapshot_failure_on_one_service(tmp_path):
    """`/api/metrics/snapshot` now uses tolerate_errors=True. A 500 from
    one service must not abort the day or the next day."""
    snapshot_calls = {"provider": 0, "manufacturer": 0, "retailer": 0}

    def factory(host: str) -> Callable[[httpx.Request], httpx.Response]:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/metrics/snapshot":
                snapshot_calls[host] += 1
                if host == "manufacturer":
                    return httpx.Response(500, json={"error": "oops"})
                return httpx.Response(200, json={"snapshotted": True})
            if request.url.path == "/api/auth/login":
                return httpx.Response(200, json={"access_token": "tok"})
            if request.url.path == "/api/inventory":
                return httpx.Response(200, json=[] if host == "retailer" else {"items": []})
            if request.url.path == "/api/customer-orders/":
                return httpx.Response(200, json=[])
            if request.url.path == "/api/catalog/":
                return httpx.Response(200, json=[])
            if request.url.path == "/api/stock/":
                return httpx.Response(200, json=[])
            if request.url.path == "/api/orders":
                return httpx.Response(200, json=[])
            return httpx.Response(200, json={"ok": True})
        return handler

    mocks = _MockServices(factory("provider"), factory("manufacturer"), factory("retailer"))
    engine = _build_engine(tmp_path, _base_config(tmp_path), _calm_scenario(), days=2)
    engine.client = httpx.Client(transport=mocks.transport(), timeout=5.0)

    engine.run()  # must NOT raise even though manufacturer 500s

    assert snapshot_calls["provider"] == 2
    assert snapshot_calls["retailer"] == 2
    # Manufacturer was called both days even though it 500'd both times
    assert snapshot_calls["manufacturer"] == 2


# ---------------------------------------------------------------------------
# Edge: nothing below threshold — fallback makes zero restock calls
# ---------------------------------------------------------------------------


def test_fallback_makes_no_restock_calls_when_everything_above_threshold(tmp_path):
    """Healthy inventory across the board: the engine must not issue any
    spurious /restock calls. This pins that the threshold checks are
    actually used."""
    restock_calls: list[str] = []

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/api/stock/restock/"):
            restock_calls.append(request.url.path)
        if request.url.path == "/api/catalog/":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/stock/":
            return httpx.Response(
                200, json=[{"product_id": 1, "quantity": 9999}]
            )
        return httpx.Response(200, json={"ok": True})

    def manufacturer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"access_token": "tok"})
        if request.url.path == "/api/orders":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/inventory":
            return httpx.Response(
                200,
                json={"items": [{"product_name": "pcb_control", "unit_type": "raw", "quantity": 9999}]},
            )
        return httpx.Response(200, json={"ok": True})

    def retailer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/inventory":
            return httpx.Response(
                200,
                json=[{"sku": "P3D-Classic", "quantity_on_hand": 9999, "retail_price": 1500.0}],
            )
        if request.url.path == "/api/customer-orders/":
            return httpx.Response(200, json=[])
        return httpx.Response(200, json={"ok": True})

    mocks = _MockServices(provider, manufacturer, retailer)
    engine = _build_engine(tmp_path, _base_config(tmp_path), _calm_scenario(), days=1)
    engine.client = httpx.Client(transport=mocks.transport(), timeout=5.0)

    engine.run()
    assert restock_calls == []


# ---------------------------------------------------------------------------
# Edge: scenario with zero days outside any event still produces baseline
# ---------------------------------------------------------------------------


def test_engine_runs_baseline_day_outside_any_scenario_event(tmp_path):
    """Day 50 with scenarios only declared up to day 5: engine must
    still send modifiers={1,1,1,1} to the provider, not skip the call."""
    received: list[dict] = []

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/scenario/effects":
            received.append(json.loads(request.content))
        if request.url.path == "/api/catalog/":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/stock/":
            return httpx.Response(200, json=[])
        return httpx.Response(200, json={"ok": True})

    def manufacturer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"access_token": "tok"})
        return httpx.Response(200, json={"items": []} if "inventory" in request.url.path else [])

    def retailer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/inventory":
            return httpx.Response(200, json=[])
        return httpx.Response(200, json={"ok": True})

    scenario = {
        "events": [
            {"start_day": 1, "end_day": 5, "demand_modifier": 5.0, "supply_modifier": 0.2}
        ]
    }
    # We jump directly to day 50 by constructing the engine and calling
    # apply_hard_effects rather than running 50 days.
    from scenario_utils import signal_for_day

    services = _MockServices(provider, manufacturer, retailer)
    engine = _build_engine(tmp_path, _base_config(tmp_path), scenario, days=1)
    engine.client = httpx.Client(transport=services.transport(), timeout=5.0)

    engine.apply_hard_effects(signal_for_day(scenario, day=50).modifiers)

    assert received == [{"lead_time_modifier": 1.0, "supply_modifier": 1.0}]


# ---------------------------------------------------------------------------
# Original test
# ---------------------------------------------------------------------------


def test_each_day_advances_then_snapshots_all_three_services(tmp_path):
    services_called: list[tuple[str, str]] = []

    def factory(host: str) -> Callable[[httpx.Request], httpx.Response]:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path in ("/api/day/advance", "/api/metrics/snapshot"):
                services_called.append((host, request.url.path))
            if request.url.path == "/api/auth/login":
                return httpx.Response(200, json={"access_token": "tok"})
            if request.url.path == "/api/inventory":
                return httpx.Response(200, json=[] if host == "retailer" else {"items": []})
            if request.url.path == "/api/customer-orders/":
                return httpx.Response(200, json=[])
            if request.url.path == "/api/catalog/":
                return httpx.Response(200, json=[])
            if request.url.path == "/api/stock/":
                return httpx.Response(200, json=[])
            if request.url.path == "/api/orders":
                return httpx.Response(200, json=[])
            return httpx.Response(200, json={"ok": True})
        return handler

    mocks = _MockServices(factory("provider"), factory("manufacturer"), factory("retailer"))
    engine = _build_engine(tmp_path, _base_config(tmp_path), _calm_scenario(), days=2)
    engine.client = httpx.Client(transport=mocks.transport(), timeout=5.0)

    engine.run()

    # Per spec: advance happens before snapshot on EACH service.
    # Per day: retailer/manufacturer/provider advance, then snapshot.
    expected_one_day_sequence = [
        ("retailer", "/api/day/advance"),
        ("manufacturer", "/api/day/advance"),
        ("provider", "/api/day/advance"),
        ("retailer", "/api/metrics/snapshot"),
        ("manufacturer", "/api/metrics/snapshot"),
        ("provider", "/api/metrics/snapshot"),
    ]
    # Two days → expect the sequence twice (back-to-back).
    assert services_called == expected_one_day_sequence * 2
