import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServiceConfig:
    name: str
    url: str
    db_path: Path


def _db_path(tier: str, entry: dict) -> Path:
    base = Path(entry.get("path", f"./{tier}").lstrip("./"))
    return base / "data" / f"{tier}.db"


def load_services(sim_json_path: Path) -> dict[str, ServiceConfig]:
    data = json.loads(Path(sim_json_path).read_text())
    provider = data["providers"][0]
    retailer = data["retailers"][0]
    manufacturer = data["manufacturer"]
    return {
        "provider": ServiceConfig(provider["name"], provider["url"].rstrip("/"), _db_path("provider", provider)),
        "manufacturer": ServiceConfig(manufacturer["name"], manufacturer["url"].rstrip("/"), _db_path("manufacturer", manufacturer)),
        "retailer": ServiceConfig(retailer["name"], retailer["url"].rstrip("/"), _db_path("retailer", retailer)),
    }
