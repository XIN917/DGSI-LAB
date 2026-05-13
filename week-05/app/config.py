"""Configuration management using environment variables."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    API_TITLE: str = "3D Printer Factory Simulator API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "REST API for production simulation"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./data/database.db"

    # Simulation
    SIMULATION_START_DAY: int = 1
    SIMULATION_TOTAL_DAYS: int = 90

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
