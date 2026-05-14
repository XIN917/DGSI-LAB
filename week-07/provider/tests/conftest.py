"""Shared test fixtures for Provider."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.database import Base

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def engine():
    """Create in-memory SQLite engine for each test."""
    eng = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
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
