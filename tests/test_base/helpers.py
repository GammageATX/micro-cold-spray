"""Test helper functions."""

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from micro_cold_spray.api.base import BaseService


def load_test_config(name: str) -> dict:
    """Load test configuration file."""
    config_path = Path(__file__).parent / "test_data" / f"{name}.json"
    with open(config_path) as f:
        return json.load(f)


def create_test_service(name: str) -> "BaseService":
    """Create a test service instance."""
    from micro_cold_spray.api.base import BaseService
    return BaseService(name)
