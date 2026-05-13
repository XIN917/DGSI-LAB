"""Pytest configuration."""

import pytest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./tests/test_database.db"

@pytest.fixture(scope="session", autouse=True)
def test_setup():
    """Setup test environment."""
    # Cleanup any old test database
    if os.path.exists("./tests/test_database.db"):
        os.remove("./tests/test_database.db")
    yield
    # Cleanup after all tests
    if os.path.exists("./tests/test_database.db"):
        os.remove("./tests/test_database.db")
