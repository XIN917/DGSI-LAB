"""Configuration file loader."""

import yaml
from pathlib import Path
from typing import Any, Dict


def load_config(config_path: str = "config/default_config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_printer_models_from_config(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract printer models from config."""
    return config.get("printer_models", [])


def get_materials_from_config(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract materials from config."""
    return config.get("materials", [])


def get_suppliers_from_config(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract suppliers from config."""
    return config.get("suppliers", [])


def get_initial_inventory_from_config(config: Dict[str, Any]) -> Dict[str, float]:
    """Extract initial inventory from config."""
    return config.get("initial_inventory", {})
