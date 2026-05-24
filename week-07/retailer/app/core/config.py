from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import AnyUrl
from pydantic import ConfigDict

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)


class RetailerSettings(BaseSettings):
    model_config = ConfigDict(env_prefix="RETAILER_")

    name: str = "PrinterWorld"
    port: int = 8003
    database_url: str = f"sqlite:///{_DATA_DIR / 'retailer.db'}"
    manufacturer_url: AnyUrl = "http://localhost:8002"
    manufacturer_username: str = "admin"
    manufacturer_password: str = "admin123"
    minimum_markup_pct: float = 15.0
    recommended_markup_pct: float = 30.0


settings = RetailerSettings()
