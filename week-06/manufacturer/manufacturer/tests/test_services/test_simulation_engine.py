"""Unit tests for SimulationEngine."""
import pytest
from decimal import Decimal
from app.services.simulation_engine import SimulationEngine


def test_load_state_from_db(db_session, sim_state):
    engine = SimulationEngine(db_session)
    assert engine.current_day == 1
    assert str(engine.current_date) == "2026-04-01"


def test_get_status(db_session, sim_state):
    engine = SimulationEngine(db_session)
    status = engine.get_status()
    assert status["current_day"] == 1
    assert status["current_date"] == "2026-04-01"
    assert status["capacity_per_day"] == 250


def test_advance_day_increments(db_session, sim_state):
    engine = SimulationEngine(db_session)
    result = engine.advance_day()
    assert result["previous_day"] == 1
    assert result["new_day"] == 2
    assert engine.current_day == 2


def test_advance_day_persists_state(db_session, sim_state):
    from app.models.simulation import SimulationState
    engine = SimulationEngine(db_session)
    engine.advance_day()

    # Reload from DB
    state = db_session.query(SimulationState).first()
    assert state.current_day == 2


def test_advance_day_returns_events(db_session, sim_state, sample_model, sample_inventory):
    """Advancing day with demand params should generate demand events."""
    import json
    from app.models.simulation import SimulationState
    # Set demand for TEST-Model
    state = db_session.query(SimulationState).first()
    state.demand_params = json.dumps({"TEST-Model": {"mean": 5, "variance": 0}})
    db_session.commit()

    engine = SimulationEngine(db_session)
    result = engine.advance_day()
    assert "events_generated" in result
    assert len(result["events_generated"]) > 0


def test_get_demand_params(db_session, sim_state):
    engine = SimulationEngine(db_session)
    params = engine.get_demand_params()
    assert "TEST-Model" in params


def test_update_demand_params(db_session, sim_state):
    from app.models.simulation import SimulationState
    engine = SimulationEngine(db_session)
    new_params = {"TEST-Model": {"mean": 20, "variance": 5}}
    engine.update_demand_params(new_params)

    # Verify it's persisted
    state = db_session.query(SimulationState).first()
    import json
    stored = json.loads(state.demand_params)
    assert stored["TEST-Model"]["mean"] == 20


def test_provider_shipped_orders_continue_polling_until_delivered(
    db_session,
    sim_state,
    monkeypatch,
):
    from datetime import datetime
    from app.models.inventory import Inventory
    from app.models.purchase_order import PurchaseOrder, Supplier

    supplier = Supplier(id=1, name="ChipSupply Co", lead_time_days=5)
    db_session.add(supplier)
    db_session.add(
        Inventory(
            product_name="provider_product_3",
            quantity=Decimal("7"),
            reserved_quantity=Decimal("0"),
            unit_type="raw",
        )
    )
    po = PurchaseOrder(
        supplier_id=1,
        product_name="provider_product_3",
        quantity_ordered=Decimal("5"),
        quantity_delivered=Decimal("0"),
        unit_cost=Decimal("10"),
        order_date=datetime(2026, 4, 1),
        expected_delivery=datetime(2026, 4, 6),
        status="shipped",
        provider_name="ChipSupply Co",
        provider_order_id=42,
    )
    db_session.add(po)
    db_session.commit()

    class FakeProviderClient:
        def __init__(self, base_url, timeout):
            pass

        def get_order_status(self, order_id):
            assert order_id == 42
            return {"id": 42, "status": "delivered"}

        def advance_day(self):
            return {"current_day": 6}

    monkeypatch.setattr(
        "app.services.provider_client.ProviderClient",
        FakeProviderClient,
    )

    engine = SimulationEngine(db_session)
    events = engine._poll_provider_orders()

    db_session.refresh(po)
    inventory = db_session.query(Inventory).filter_by(
        product_name="provider_product_3"
    ).first()
    assert po.status == "delivered"
    assert po.quantity_delivered == Decimal("5.00")
    assert inventory.quantity == Decimal("12.00")
    assert events[0]["type"] == "provider_order_delivered"
