"""Test helper functions."""

from pathlib import Path
import yaml
import shutil
from datetime import datetime

from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata


def get_config_dir() -> Path:
    """Get the real config directory."""
    return Path("micro_cold_spray/api/config")


def get_schema_dir() -> Path:
    """Get the real schema directory."""
    return get_config_dir() / "schemas"


def load_yaml_file(file_path: Path) -> dict:
    """Load YAML file."""
    with open(file_path) as f:
        return yaml.load(f, Loader=yaml.Loader)


def load_config(name: str) -> dict:
    """Load a config file from the real config directory."""
    config_path = get_config_dir() / f"{name}.yaml"
    return load_yaml_file(config_path)


def create_config_data(name: str, data: dict = None) -> ConfigData:
    """Create a ConfigData object for testing."""
    if data is None:
        data = load_config(name)
    
    metadata = ConfigMetadata(
        config_type=name,
        last_modified=datetime.now(),
        version="1.0.0"
    )
    return ConfigData(metadata=metadata, data=data)


def setup_test_config(tmp_path: Path, name: str) -> Path:
    """Set up a test config file using real config as template."""
    real_config = get_config_dir() / f"{name}.yaml"
    test_config = tmp_path / f"{name}.yaml"
    shutil.copy2(real_config, test_config)
    return test_config


def create_test_config(tmp_path: Path, name: str, data: dict) -> Path:
    """Create a test config file with given data.
    
    Args:
        tmp_path: Temporary directory path
        name: Config name
        data: Config data to write
        
    Returns:
        Path to created config file
    """
    test_config = tmp_path / f"{name}.yaml"
    with open(test_config, "w") as f:
        yaml.dump(data, f)
    return test_config
