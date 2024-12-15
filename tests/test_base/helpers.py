"""Test helper functions."""

import json
import yaml
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from micro_cold_spray.api.base import BaseService


def load_test_config(name: str, format: str = "yaml") -> Dict[str, Any]:
    """Load test configuration file.
    
    Args:
        name: Name of the config file without extension
        format: Format of the config file ('yaml' or 'json')
        
    Returns:
        Loaded configuration data
    """
    test_config_dir = Path(__file__).parent.parent / "test_config" / "test_data"
    
    if format == "json":
        config_path = test_config_dir / "schemas" / f"{name}.json"
        with open(config_path) as f:
            return json.load(f)
    else:
        config_path = test_config_dir / f"{name}.yaml"
        with open(config_path) as f:
            return yaml.load(f)


def create_test_service(name: str) -> "BaseService":
    """Create a test service instance."""
    from micro_cold_spray.api.base import BaseService
    return BaseService(name)
