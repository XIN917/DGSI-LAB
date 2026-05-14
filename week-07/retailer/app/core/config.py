from pydantic_settings import BaseSettings
from pydantic import AnyUrl
from pydantic import ConfigDict


class RetailerSettings(BaseSettings):
    model_config = ConfigDict(env_prefix="RETAILER_")

    port: int = 8003
    database_url: str = "sqlite+aiosqlite:///data/retailer.db"
    manufacturer_url: AnyUrl = "http://localhost:8002"
    manufacturer_username: str = "admin"
    manufacturer_password: str = "admin123"
    minimum_markup_pct: float = 15.0
    recommended_markup_pct: float = 30.0


settings = RetailerSettings()
