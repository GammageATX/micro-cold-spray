"""Test configuration fixtures and base class."""

import pytest
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.base.base_errors import ServiceError, ConfigError
from micro_cold_spray.api.base.base_configurable import ConfigurableService


class BaseConfigTest:
    """Base class for configuration tests."""
    
    def verify_error_response(self, error, expected_status: int, expected_message: str) -> None:
        """Verify error response matches expected format.
        
        Args:
            error: Error response to verify
            expected_status: Expected HTTP status code
            expected_message: Expected error message
        """
        assert error.value.status_code == expected_status
        assert expected_message in str(error.value)
        assert hasattr(error.value, "context")

    async def verify_service_health(self, service, expected_healthy: bool = True) -> None:
        """Verify service health check.
        
        Args:
            service: Service to check health for
            expected_healthy: Expected health status
        """
        health = await service.check_health()
        assert health["is_healthy"] == expected_healthy
        assert "status" in health
        assert "uptime" in health
        assert "service_info" in health

    def verify_config_response(self, response, expected_status: int) -> None:
        """Verify configuration API response.
        
        Args:
            response: API response to verify
            expected_status: Expected HTTP status code
        """
        assert response.status_code == expected_status
        if expected_status == status.HTTP_200_OK:
            assert "data" in response.json()
        else:
            assert "detail" in response.json()

    async def verify_service_start(self, service) -> None:
        """Verify service startup.
        
        Args:
            service: Service to verify
        """
        await service.start()
        assert service.is_running
        assert service.start_time is not None
        assert service.uptime > 0

    async def verify_service_stop(self, service) -> None:
        """Verify service shutdown.
        
        Args:
            service: Service to verify
        """
        await service.stop()
        assert not service.is_running
        assert service.start_time is None
        assert service.uptime is None


@pytest.fixture
def test_config_dir(tmp_path) -> Path:
    """Create temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def test_config_data() -> ConfigData:
    """Create test configuration data."""
    return ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            created=datetime.now(),
            last_modified=datetime.now(),
            version="1.0.0"
        ),
        data={"key": "value"}
    )


@pytest.fixture
def test_config_schema() -> Dict[str, Any]:
    """Create test configuration schema."""
    return {
        "type": "object",
        "title": "Test Configuration",
        "description": "Schema for testing",
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "number"}
        },
        "required": ["key"]
    }


@pytest.fixture
def test_config_file(test_config_dir: Path, test_config_data: ConfigData) -> Path:
    """Create test configuration file."""
    import yaml
    
    config_path = test_config_dir / "test.yaml"
    with open(config_path, "w") as f:
        yaml.safe_dump(test_config_data.model_dump(), f)
    return config_path


@pytest.fixture
def test_schema_dir(test_config_dir: Path) -> Path:
    """Create test schema directory."""
    schema_dir = test_config_dir / "schemas"
    schema_dir.mkdir()
    return schema_dir


@pytest.fixture
def test_backup_dir(test_config_dir: Path) -> Path:
    """Create test backup directory."""
    backup_dir = test_config_dir / "backups"
    backup_dir.mkdir()
    return backup_dir


@pytest.fixture
async def base_service() -> AsyncGenerator[ConfigurableService, None]:
    """Create base service fixture."""
    service = ConfigurableService(service_name="test")
    await service.start()
    yield service
    await service.stop()


@pytest.fixture
async def config_service(test_config_dir: Path) -> AsyncGenerator[ConfigService, None]:
    """Create config service fixture."""
    service = ConfigService("config")
    service._config_dir = test_config_dir
    await service.start()
    yield service
    await service.stop()


@pytest.fixture
def test_app(test_config_dir: Path) -> FastAPI:
    """Create test application."""
    from micro_cold_spray.api.config.config_app import ConfigApp
    app = ConfigApp(config_dir=test_config_dir)
    return app


@pytest.fixture
def test_client(test_app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator:
    """Create async test client."""
    from httpx import AsyncClient
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client
