"""Shared test fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.models.product import ProductModel, BOMItem
from app.models.inventory import Inventory
from app.models.purchase_order import Supplier, SupplierProduct
from app.models.simulation import SimulationState
from decimal import Decimal

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def engine():
    """Create in-memory SQLite engine for each test."""
    eng = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    from app.models import user, product, inventory, order, purchase_order, event, simulation  # noqa
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture(scope="function")
def db_session(engine):
    """Provide a fresh DB session for each test."""
    session = Session(engine)
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def admin_user(db_session):
    """Create an admin test user."""
    user = User(
        username="testadmin",
        password_hash=get_password_hash("password123"),
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_inventory(db_session):
    """Seed minimal inventory data."""
    items = [
        Inventory(product_name="frame_kit", quantity=Decimal("100"), reserved_quantity=Decimal("0"), unit_type="raw"),
        Inventory(product_name="pcb_control", quantity=Decimal("50"), reserved_quantity=Decimal("0"), unit_type="raw"),
        Inventory(product_name="stepper_motor", quantity=Decimal("200"), reserved_quantity=Decimal("0"), unit_type="raw"),
        Inventory(product_name="hotend", quantity=Decimal("80"), reserved_quantity=Decimal("0"), unit_type="raw"),
        Inventory(product_name="bed_heater", quantity=Decimal("80"), reserved_quantity=Decimal("0"), unit_type="raw"),
        Inventory(product_name="power_supply", quantity=Decimal("80"), reserved_quantity=Decimal("0"), unit_type="raw"),
        Inventory(product_name="extruder_kit", quantity=Decimal("80"), reserved_quantity=Decimal("0"), unit_type="raw"),
    ]
    for item in items:
        db_session.add(item)
    db_session.commit()
    return items


@pytest.fixture
def sample_model(db_session):
    """Create a sample product model with BOM."""
    model = ProductModel(id="TEST-Model", name="Test Printer", assembly_time_days=1)
    db_session.add(model)
    bom_items = [
        BOMItem(model_id="TEST-Model", material_name="frame_kit", quantity_required=Decimal("1")),
        BOMItem(model_id="TEST-Model", material_name="pcb_control", quantity_required=Decimal("1")),
        BOMItem(model_id="TEST-Model", material_name="stepper_motor", quantity_required=Decimal("2")),
        BOMItem(model_id="TEST-Model", material_name="hotend", quantity_required=Decimal("1")),
        BOMItem(model_id="TEST-Model", material_name="bed_heater", quantity_required=Decimal("1")),
        BOMItem(model_id="TEST-Model", material_name="power_supply", quantity_required=Decimal("1")),
        BOMItem(model_id="TEST-Model", material_name="extruder_kit", quantity_required=Decimal("1")),
    ]
    for b in bom_items:
        db_session.add(b)
    db_session.commit()
    return model


@pytest.fixture
def sim_state(db_session):
    """Seed a simulation state row."""
    import json
    state = SimulationState(
        current_day=1,
        current_date="2026-04-01",
        demand_params=json.dumps({"TEST-Model": {"mean": 5, "variance": 1}}),
        capacity_per_day=250,
        warehouse_capacity=1000,
    )
    db_session.add(state)
    db_session.commit()
    return state
