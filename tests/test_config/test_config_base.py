"""Tests for configuration base classes."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel, Field

from micro_cold_spray.api.base.base_errors import ServiceError, ConfigError
from micro_cold_spray.api.base.base_configurable import ConfigurableService


class TestConfigModel(BaseModel):
    """Test configuration model."""
    test_field: str = Field(default="test")
    test_value: int = Field(default=42)


@pytest.fixture
def config_base_service() -> ConfigurableService:
    """Create test configurable service."""
    service = ConfigurableService(service_name="test", config_model=TestConfigModel)
    service._file_service = MagicMock()
    service._schema_service = MagicMock()
    service._cache_service = MagicMock()
    service._format_service = MagicMock()
    service._registry_service = MagicMock()
    return service


@pytest.mark.asyncio
async def test_service_lifecycle(config_base_service):
    """Test service lifecycle (start/stop)."""
    # Mock service dependencies
    config_base_service._file_service.start = AsyncMock()
    config_base_service._schema_service.start = AsyncMock()
    config_base_service._cache_service.start = AsyncMock()
    config_base_service._format_service.start = AsyncMock()
    config_base_service._registry_service.start = AsyncMock()
    
    config_base_service._file_service.stop = AsyncMock()
    config_base_service._schema_service.stop = AsyncMock()
    config_base_service._cache_service.stop = AsyncMock()
    config_base_service._format_service.stop = AsyncMock()
    config_base_service._registry_service.stop = AsyncMock()
    
    # Start service
    await config_base_service.start()
    assert config_base_service.is_running
    
    # Stop service
    await config_base_service.stop()
    assert not config_base_service.is_running


@pytest.mark.asyncio
async def test_health_check(config_base_service):
    """Test health check."""
    # Start service
    config_base_service.is_running = True
    
    # Check health
    health = await config_base_service.check_health()
    assert health["status"] == "healthy"
    assert "uptime" in health


@pytest.mark.asyncio
async def test_service_error_handling(config_base_service):
    """Test service error handling."""
    # Mock service dependencies to raise errors
    config_base_service._file_service.start = AsyncMock(side_effect=Exception("File service error"))
    
    # Verify service start fails with wrapped error
    with pytest.raises(ServiceError) as exc_info:
        await config_base_service.start()
    assert "File service error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_service_dependencies(config_base_service):
    """Test service dependency management."""
    # Mock service dependencies
    config_base_service._file_service.is_ready = AsyncMock(return_value=True)
    config_base_service._schema_service.is_ready = AsyncMock(return_value=True)
    config_base_service._cache_service.is_ready = AsyncMock(return_value=True)
    config_base_service._format_service.is_ready = AsyncMock(return_value=True)
    config_base_service._registry_service.is_ready = AsyncMock(return_value=True)
    
    # Start service
    await config_base_service.start()
    assert config_base_service.is_running


@pytest.mark.asyncio
async def test_service_dependency_failure(config_base_service):
    """Test service dependency failure handling."""
    # Mock service dependencies with one failing
    config_base_service._file_service.is_ready = AsyncMock(return_value=True)
    config_base_service._schema_service.is_ready = AsyncMock(return_value=False)
    
    # Verify service start fails due to dependency
    with pytest.raises(ServiceError) as exc_info:
        await config_base_service.start()
    assert "Schema service not ready" in str(exc_info.value)
