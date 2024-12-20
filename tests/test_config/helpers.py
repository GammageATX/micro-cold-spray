"""Test helper functions."""

from pathlib import Path
import yaml
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata
from micro_cold_spray.api.base.base_errors import create_error


def create_test_config_data(
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
        : Created config data object
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
    config_dir: Path,
    name: str,
    data: Dict[str, Any]
) -> Path:
    """Create a test config file.
    
    Args:
        config_dir: Config directory path
        name: Config name
        data: Config data to write
        
    Returns:
        Path: Path to created config file
        
    Raises:
        : If file creation fails
    """
    try:
        config_path = config_dir / f"{name}.yaml"
        with open(config_path, "w") as f:
            yaml.safe_dump(data, f)
        return config_path
    except Exception as e:
        raise create_error(
            status_code=500,
            message=f"Failed to create test config file: {e}",
            context={"name": name, "path": str(config_path)}
        )


def create_test_schema_file(
    schema_dir: Path,
    name: str,
    schema: Dict[str, Any]
) -> Path:
    """Create a test schema file.
    
    Args:
        schema_dir: Schema directory path
        name: Schema name
        schema: Schema data to write
        
    Returns:
        Path: Path to created schema file
        
    Raises:
        : If file creation fails
    """
    try:
        schema_path = schema_dir / f"{name}.json"
        import json
        with open(schema_path, "w") as f:
            json.dump(schema, f, indent=2)
        return schema_path
    except Exception as e:
        raise create_error(
            status_code=500,
            message=f"Failed to create test schema file: {e}",
            context={"name": name, "path": str(schema_path)}
        )


def verify_config_data(
    config: ConfigData,
    expected_type: str,
    expected_data: Dict[str, Any],
    ignore_timestamps: bool = True
) -> None:
    """Verify config data matches expected values.
    
    Args:
        config: Config data to verify
        expected_type: Expected config type
        expected_data: Expected config data
        ignore_timestamps: Whether to ignore timestamp fields
    """
    assert config.metadata.config_type == expected_type
    assert config.data == expected_data
    if not ignore_timestamps:
        assert config.metadata.last_modified is not None


def verify_file_contents(
    file_path: Path,
    expected_data: Union[Dict[str, Any], List[Any]]
) -> None:
    """Verify file contents match expected data.
    
    Args:
        file_path: Path to file
        expected_data: Expected file contents
        
    Raises:
        : If file verification fails
    """
    try:
        with open(file_path) as f:
            if file_path.suffix == ".json":
                import json
                actual_data = json.load(f)
            else:
                actual_data = yaml.safe_load(f)
        assert actual_data == expected_data
    except Exception as e:
        raise create_error(
            status_code=500,
            message=f"Failed to verify file contents: {e}",
            context={"path": str(file_path)}
        )
