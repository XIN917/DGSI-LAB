"""Application settings and configuration."""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App settings
    APP_NAME: str = "3D Printer Production Simulator"
    APP_VERSION: str = "0.1.0"

    # Security
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    DATABASE_URL: str = "sqlite:///./data/simulation.db"

    # Simulation defaults
    DEFAULT_CAPACITY_PER_DAY: int = 250
    DEFAULT_WAREHOUSE_CAPACITY: int = 1000
    SIMULATION_START_DATE: str = "2026-04-01"

    # Seed data
    SEED_SAMPLE_DATA: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
