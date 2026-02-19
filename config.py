"""
Load monitor config from config.yaml.
"""
from pathlib import Path
import yaml


def load_config(path: str | Path = "config.yaml") -> dict:
    """Load and return the config dict from path (default config.yaml)."""
    with open(path) as f:
        return yaml.safe_load(f)
