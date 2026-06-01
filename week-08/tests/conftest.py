import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_addoption(parser):
    parser.addoption(
        "--run-ui", action="store_true", default=False,
        help="Run UI tests against the live dashboard at localhost:8080",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "ui: live browser tests — require --run-ui and running services")
