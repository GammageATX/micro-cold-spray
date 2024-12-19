"""Test helper functions."""

from pathlib import Path
import yaml
import shutil
from datetime import datetime
from typing import Dict, Any, Optional

from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata


def load_yaml_file(file_path: Path) -> dict:
    """Load YAML file.
    
    Args:
        file_path: Path to YAML file
        
    Returns:
        dict: Loaded YAML data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If file contains invalid YAML
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path) as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in {file_path}: {e}")


def create_config_data(
    config_type: str,
    data: Optional[Dict[str, Any]] = None,
    version: str = "1.0.0"
) -> ConfigData:
    """Create a ConfigData object for testing.
    
    Args:
        config_type: Configuration type
        data: Configuration data (optional)
        version: Configuration version (optional)
        
    Returns:
        ConfigData: Created config data object
    """
    if data is None:
        data = {"test_key": "test_value"}
    
    metadata = ConfigMetadata(
        config_type=config_type,
        last_modified=datetime.now(),
        version=version
    )
    return ConfigData(metadata=metadata, data=data)


def create_test_config_file(
    tmp_path: Path,
    name: str,
    data: Dict[str, Any]
) -> Path:
    """Create a test config file.
    
    Args:
        tmp_path: Temporary directory path
        name: Config name
        data: Config data to write
        
    Returns:
        Path: Path to created config file
        
    Raises:
        yaml.YAMLError: If data cannot be serialized to YAML
    """
    config_path = tmp_path / f"{name}.yaml"
    with open(config_path, "w") as f:
        try:
            yaml.safe_dump(data, f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to write config data: {e}")
    return config_path


def copy_test_config(
    src_path: Path,
    dst_path: Path,
    make_backup: bool = True
) -> Path:
    """Copy a test config file.
    
    Args:
        src_path: Source file path
        dst_path: Destination file path
        make_backup: Whether to create backup of existing file
        
    Returns:
        Path: Path to copied file
        
    Raises:
        FileNotFoundError: If source file doesn't exist
        OSError: If copy operation fails
    """
    if not src_path.exists():
        raise FileNotFoundError(f"Source file not found: {src_path}")
    
    if make_backup and dst_path.exists():
        backup_path = dst_path.with_suffix(".bak")
        shutil.copy2(dst_path, backup_path)
    
    try:
        return Path(shutil.copy2(src_path, dst_path))
    except OSError as e:
        raise OSError(f"Failed to copy config file: {e}")


def compare_config_data(
    config1: ConfigData,
    config2: ConfigData,
    ignore_metadata: bool = False
) -> bool:
    """Compare two ConfigData objects.
    
    Args:
        config1: First config
        config2: Second config
        ignore_metadata: Whether to ignore metadata in comparison
        
    Returns:
        bool: True if configs are equal
    """
    if not ignore_metadata:
        return config1 == config2
    
    return config1.data == config2.data
