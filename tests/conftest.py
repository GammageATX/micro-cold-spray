"""Common test fixtures and configuration."""

import pytest
from pathlib import Path
from typing import Generator, Any
from unittest.mock import AsyncMock, PropertyMock
from datetime import datetime

from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata


@pytest.fixture
def test_config() -> dict[str, Any]:
    """Test configuration data."""
    return {
        "key": "value",
        "number": 123,
        "nested": {
            "inner": "data"
        }
    }


@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Path:
    """Create temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture(autouse=True)
def setup_test_env() -> Generator[None, None, None]:
    """Setup test environment before each test."""
    # Clear service registry
    from micro_cold_spray.api.base import _services
    _services.clear()
    yield


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    service = AsyncMock()
    type(service).is_initialized = PropertyMock(return_value=True)
    type(service).is_running = PropertyMock(return_value=True)
    
    # Mock get_config to return proper config data
    async def mock_get_config(config_type: str):
        return ConfigData(
            metadata=ConfigMetadata(
                config_type=config_type,
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={
                "test": "value",
                "network": {
                    "plc": {
                        "host": "localhost",
                        "port": 502
                    }
                }
            }
        )
    service.get_config.side_effect = mock_get_config
    return service
