"""Tests for simulation day API behavior."""
from app.api.endpoints.day import advance_day
from app.api.endpoints import simulation as simulation_endpoint
from app.services.external_supplier_service import ExternalSupplierService
from app.services.simulation_engine import SimulationEngine


def test_day_advance_polls_external_suppliers_before_advancing(monkeypatch, db_session):
    calls = []

    def fake_poll_orders(self):
        calls.append("poll")

    def fake_advance_day(self):
        calls.append("advance")
        return {
            "previous_day": 1,
            "new_day": 2,
            "current_date": "2026-04-02",
            "events_generated": [],
        }

    monkeypatch.setattr(ExternalSupplierService, "poll_orders", fake_poll_orders)
    monkeypatch.setattr(SimulationEngine, "advance_day", fake_advance_day)

    result = advance_day(db_session)

    assert calls == ["poll", "advance"]
    assert result["new_day"] == 2


def test_simulation_advance_polls_external_suppliers_before_advancing(monkeypatch, db_session):
    calls = []

    def fake_poll_orders(self):
        calls.append("poll")

    def fake_advance_day(self):
        calls.append("advance")
        return {
            "previous_day": 1,
            "new_day": 2,
            "current_date": "2026-04-02",
            "events_generated": [],
        }

    monkeypatch.setattr(ExternalSupplierService, "poll_orders", fake_poll_orders)
    monkeypatch.setattr(SimulationEngine, "advance_day", fake_advance_day)

    result = simulation_endpoint.advance_day(db=db_session)

    assert calls == ["poll", "advance"]
    assert result["new_day"] == 2
