import json
from pathlib import Path
from dashboard.config import load_services, ServiceConfig


def test_load_services_maps_three_tiers(tmp_path):
    sim = {
        "retailers": [{"name": "PrinterWorld", "url": "http://127.0.0.1:8003", "path": "./retailer"}],
        "manufacturer": {"name": "Factory", "url": "http://127.0.0.1:8002", "path": "./manufacturer"},
        "providers": [{"name": "ChipSupply", "url": "http://127.0.0.1:8001", "path": "./provider"}],
    }
    cfg = tmp_path / "sim.json"
    cfg.write_text(json.dumps(sim))

    services = load_services(cfg)

    assert set(services) == {"provider", "manufacturer", "retailer"}
    assert services["provider"] == ServiceConfig(
        name="ChipSupply", url="http://127.0.0.1:8001", db_path=Path("provider/data/provider.db"))
    assert services["manufacturer"].url == "http://127.0.0.1:8002"
    assert services["retailer"].db_path == Path("retailer/data/retailer.db")
