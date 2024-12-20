"""Tests for configuration cache service."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timedelta

from micro_cold_spray.api.config.services.cache_service import ConfigCacheService
from micro_cold_spray.api.base.base_errors import ConfigError, ServiceError
from micro_cold_spray.api.config.models import ConfigData


@pytest.fixture
async def cache_service():
    """Create a cache service instance."""
    service = ConfigCacheService(service_name="cache")
    return service


@pytest.mark.asyncio
async def test_service_lifecycle(cache_service):
    """Test service lifecycle."""
    # Start service
    await cache_service.start()
    assert cache_service.is_running
    
    # Stop service
    await cache_service.stop()
    assert not cache_service.is_running


@pytest.mark.asyncio
async def test_service_start_error(cache_service):
    """Test service start error handling."""
    # Mock to raise error
    cache_service._initialize = AsyncMock(side_effect=Exception("Test error"))
    
    with pytest.raises(ServiceError) as exc_info:
        await cache_service.start()
    assert "Test error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_service_stop_error(cache_service):
    """Test service stop error handling."""
    # Start service
    await cache_service.start()
    
    # Mock to raise error
    cache_service._cleanup = AsyncMock(side_effect=Exception("Test error"))
    
    with pytest.raises(ServiceError) as exc_info:
        await cache_service.stop()
    assert "Test error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cache_entry_validation(cache_service):
    """Test cache entry validation."""
    # Start service
    await cache_service.start()
    
    # Test invalid entry
    with pytest.raises(ConfigError):
        await cache_service.validate_cache_entry(None)
    
    # Test valid entry
    entry = {
        "timestamp": datetime.now(),
        "data": {"test": "data"}
    }
    assert await cache_service.validate_cache_entry(entry)


@pytest.mark.asyncio
async def test_cache_config(cache_service):
    """Test caching configuration."""
    # Start service
    await cache_service.start()
    
    # Create test config
    config = ConfigData(
        metadata={
            "config_type": "test",
            "version": "1.0.0",
            "last_modified": datetime.now()
        },
        data={"test": "data"}
    )
    
    # Cache config
    await cache_service.cache_config("test", config)
    
    # Get cached config
    cached = await cache_service.get_cached_config("test")
    assert cached == config


@pytest.mark.asyncio
async def test_get_cached_config_missing(cache_service):
    """Test getting missing cached config."""
    # Start service
    await cache_service.start()
    
    # Get non-existent config
    result = await cache_service.get_cached_config("missing")
    assert result is None


@pytest.mark.asyncio
async def test_get_cached_config_expired(cache_service):
    """Test getting expired cached config."""
    # Start service
    await cache_service.start()
    
    # Create expired entry
    expired_time = datetime.now() - timedelta(hours=2)
    cache_service._cache["test"] = {
        "timestamp": expired_time,
        "data": {"test": "data"}
    }
    
    # Get expired config
    result = await cache_service.get_cached_config("test")
    assert result is None


@pytest.mark.asyncio
async def test_cache_config_invalid(cache_service):
    """Test caching invalid config."""
    # Start service
    await cache_service.start()
    
    with pytest.raises(ConfigError):
        await cache_service.cache_config("test", None)


@pytest.mark.asyncio
async def test_cache_config_error(cache_service):
    """Test cache error handling."""
    # Start service
    await cache_service.start()
    
    # Mock to raise error
    cache_service._validate_config = AsyncMock(side_effect=Exception("Test error"))
    
    with pytest.raises(ConfigError) as exc_info:
        await cache_service.cache_config("test", {"test": "data"})
    assert "Test error" in str(exc_info.value)
