"""Configuration test fixtures."""

import pytest
import asyncio
from pathlib import Path
import yaml
from datetime import datetime

from micro_cold_spray.__main__ import get_test_config
from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.config_app import ConfigApp
from micro_cold_spray.api.base.base_errors import ConfigError
from micro_cold_spray.api.base.base_registry import register_service
import uvicorn

# Import base test utilities
from tests.test_config.config_test_base import create_test_app, create_test_client
# Import but don't redefine base fixtures
from tests.fixtures.base import test_app_with_cors  # noqa: F401


@pytest.fixture
async def config_base_service():
    """Create base config service with proper lifecycle.
    
    Returns:
        ConfigService: Configured service instance
    """
    service = ConfigService()
    register_service(service)
    
    # Configure service with default config
    config_data = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now(),
            version="1.0.0"
        ),
        data={
            "config_dir": "config",
            "schema_dir": "config/schemas",
            "enable_cache": True,
            "cache_ttl": 300,
            "backup_enabled": True,
            "backup_dir": "config/backups"
        }
    )
    
    await service.configure(config_data.model_dump())
    await service.start()
    yield service
    await service.stop()


@pytest.fixture
def mock_service_error():
    """Create standardized service error mock.
    
    Returns:
        ConfigError: Standard error for service tests
    """
    return ConfigError("Service error")


@pytest.fixture(scope="function")
async def config_server():
    """Start a test config server instance.
    
    Returns:
        str: Server URL
    """
    config = get_test_config('config')
    server = uvicorn.Server(config)
    
    # Start server in background
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(1)  # Give server time to start
    
    yield f"http://127.0.0.1:{config.port}"
    
    # Cleanup
    server.should_exit = True
    await server_task


@pytest.fixture
def config_app(config_base_service):
    """Create test config app instance.
    
    Args:
        config_base_service: Base config service fixture
    
    Returns:
        ConfigApp: App instance
    """
    return create_test_app(ConfigService)


@pytest.fixture
def test_client(config_app, config_base_service):
    """Create test client.
    
    Args:
        config_app: Config app fixture
        config_base_service: Base config service fixture
    
    Returns:
        TestClient: FastAPI test client
    """
    return create_test_client(config_app, config_base_service)


@pytest.fixture
def test_config_dir(tmp_path):
    """Create a temporary config directory.
    
    Returns:
        Path: Config directory path
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def test_schema_dir(test_config_dir):
    """Create a temporary schema directory.
    
    Returns:
        Path: Schema directory path
    """
    schema_dir = test_config_dir / "schemas"
    schema_dir.mkdir()
    return schema_dir


@pytest.fixture
def test_config_data():
    """Create test configuration data.
    
    Returns:
        ConfigData: Test config data
    """
    return ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now(),
            version="1.0.0"
        ),
        data={"key": "value"}
    )
