"""Helper functions for config tests."""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata


def get_test_data_dir() -> Path:
    """Get the test data directory path."""
    return Path(__file__).parent / "test_data"


def get_test_schema_dir() -> Path:
    """Get the test schema directory path."""
    return get_test_data_dir() / "schemas"


def get_test_backup_dir() -> Path:
    """Get the test backup directory path."""
    return get_test_data_dir() / "backups"


def load_test_config(name: str) -> Dict[str, Any]:
    """Load a test YAML config file.
    
    Args:
        name: Name of the config file without extension
        
    Returns:
        Loaded configuration data
    """
    config_path = get_test_data_dir() / f"{name}.yaml"
    return load_yaml_file(config_path)


def load_yaml_file(path: Path) -> Dict[str, Any]:
    """Load a YAML file from any path.
    
    Args:
        path: Path to the YAML file
        
    Returns:
        Loaded YAML data
    """
    with open(path) as f:
        return yaml.safe_load(f)


def load_test_schema(name: str) -> Dict[str, Any]:
    """Load a test JSON schema file.
    
    Args:
        name: Name of the schema file without extension
        
    Returns:
        Loaded schema data
    """
    schema_path = get_test_schema_dir() / f"{name}.json"
    with open(schema_path) as f:
        return json.load(f)


def create_test_config_data(
    config_type: str,
    data: Optional[Dict[str, Any]] = None
) -> ConfigData:
    """Create a ConfigData instance for testing.
    
    Args:
        config_type: Type of configuration
        data: Configuration data (if None, loads from test_config.yaml)
        
    Returns:
        ConfigData instance
    """
    if data is None:
        data = load_test_config("test_config")
        
    metadata = ConfigMetadata(
        config_type=config_type,
        last_modified=datetime.now()
    )
    
    return ConfigData(metadata=metadata, data=data) 