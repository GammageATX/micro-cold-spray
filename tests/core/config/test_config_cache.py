"""Tests for config cache service."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from fastapi import status, HTTPException

from micro_cold_spray.api.config.services.cache_service import ConfigCacheService, CacheEntry
from micro_cold_spray.api.base import BaseService
from .helpers import create_config_data


@pytest.fixture
def cache_service():
    """Create cache service."""
    return ConfigCacheService()


@pytest.fixture
def test_config():
    """Create test config data."""
    return create_config_data(
        name="test",
        data={"key": "value"}
    )


@pytest.fixture
def test_configs():
    """Create multiple test configs."""
    return {
        "test1": create_config_data(
            name="test1",
            data={"key1": "value1"}
        ),
        "test2": create_config_data(
            name="test2",
            data={"key2": "value2"}
        )
    }


@pytest.mark.asyncio
async def test_service_start_stop(cache_service):
    """Test service startup and shutdown."""
    # Start service
    await cache_service.start()
    assert cache_service.is_running
    assert len(cache_service._cache) == 0
    
    # Check health
    health = await cache_service._check_health()
    assert health["cache_size"] == 0
    assert "last_cleanup" in health
    
    # Stop service
    await cache_service.stop()
    assert not cache_service.is_running
    assert len(cache_service._cache) == 0


@pytest.mark.asyncio
async def test_service_start_error():
    """Test service startup with error."""
    service = ConfigCacheService()
    
    # Mock start to raise an error
    with patch.object(BaseService, 'start', side_effect=Exception("Start error")):
        with pytest.raises(HTTPException) as exc_info:
            await service.start()
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Start error" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_service_stop_error():
    """Test service shutdown with error."""
    service = ConfigCacheService()
    await service.start()
    
    # Mock stop to raise an error
    with patch.object(BaseService, 'stop', side_effect=Exception("Stop error")):
        with pytest.raises(HTTPException) as exc_info:
            await service.stop()
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Stop error" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_cache_entry_validation(test_config):
    """Test cache entry validation."""
    # Test with None config
    with pytest.raises(ValueError, match="Config data cannot be None"):
        CacheEntry(None)
    
    # Test with invalid data
    invalid_config = test_config.model_copy()
    invalid_config.data = None
    with pytest.raises(ValueError, match="Invalid config data"):
        CacheEntry(invalid_config)


@pytest.mark.asyncio
async def test_cache_config(cache_service, test_config):
    """Test caching configuration."""
    # Start service
    await cache_service.start()
    
    # Cache config
    await cache_service.cache_config("test", test_config)
    
    # Verify config was cached
    cached = await cache_service.get_cached_config("test")
    assert cached == test_config
    
    # Verify cache entry
    assert "test" in cache_service._cache
    assert isinstance(cache_service._cache["test"], CacheEntry)
    assert cache_service._cache["test"].data == test_config


@pytest.mark.asyncio
async def test_get_cached_config_missing(cache_service):
    """Test getting non-existent cached config."""
    # Start service
    await cache_service.start()
    
    # Get non-existent config
    cached = await cache_service.get_cached_config("nonexistent")
    assert cached is None


@pytest.mark.asyncio
async def test_get_cached_config_expired(cache_service, test_config):
    """Test getting expired cached config."""
    # Start service
    await cache_service.start()
    
    # Create expired cache entry
    entry = CacheEntry(test_config, ttl=1)  # 1 second TTL
    entry.timestamp = datetime.now() - timedelta(seconds=2)  # Make it expired
    cache_service._cache["test"] = entry
    
    # Get expired config
    cached = await cache_service.get_cached_config("test")
    assert cached is None


@pytest.mark.asyncio
async def test_remove_from_cache(cache_service, test_config):
    """Test removing cached config."""
    # Start service
    await cache_service.start()
    
    # Create cache entry
    entry = CacheEntry(test_config)
    cache_service._cache["test"] = entry
    
    # Remove config
    await cache_service.remove_from_cache("test")
    
    # Verify config was removed
    assert "test" not in cache_service._cache
    cached = await cache_service.get_cached_config("test")
    assert cached is None


@pytest.mark.asyncio
async def test_remove_from_cache_missing(cache_service):
    """Test removing non-existent cached config."""
    # Start service
    await cache_service.start()
    
    # Remove non-existent config
    await cache_service.remove_from_cache("nonexistent")
    
    # Verify no error was raised
    assert True


@pytest.mark.asyncio
async def test_clear_cache(cache_service, test_configs):
    """Test clearing entire cache."""
    # Start service
    await cache_service.start()
    
    # Create cache entries
    for config_type, config in test_configs.items():
        entry = CacheEntry(config)
        cache_service._cache[config_type] = entry
    
    # Clear cache
    await cache_service.clear_cache()
    
    # Verify all configs were removed
    assert len(cache_service._cache) == 0
    for config_type in test_configs:
        cached = await cache_service.get_cached_config(config_type)
        assert cached is None


@pytest.mark.asyncio
async def test_cache_config_update(cache_service, test_config):
    """Test updating cached config."""
    # Start service
    await cache_service.start()
    
    # Create initial config
    initial_config = test_config
    
    # Cache initial config
    await cache_service.cache_config("test", initial_config)
    
    # Create updated config
    updated_config = create_config_data(
        name="test",
        data={"key": "updated_value"}
    )
    
    # Cache updated config
    await cache_service.cache_config("test", updated_config)
    
    # Verify config was updated
    cached = await cache_service.get_cached_config("test")
    assert cached == updated_config
    assert cached.data["key"] == "updated_value"


@pytest.mark.asyncio
async def test_cache_cleanup(cache_service, test_configs):
    """Test cache cleanup of expired entries."""
    # Start service
    await cache_service.start()
    
    # Create mix of expired and valid entries
    for config_type, config in test_configs.items():
        entry = CacheEntry(config, ttl=1)  # 1 second TTL
        if config_type == "test1":
            # Make test1 expired
            entry.timestamp = datetime.now() - timedelta(seconds=2)
        cache_service._cache[config_type] = entry
    
    # Run cleanup
    await cache_service._cleanup_cache()
    
    # Verify expired entries were removed
    assert "test1" not in cache_service._cache
    assert "test2" in cache_service._cache


@pytest.mark.asyncio
async def test_cache_cleanup_error(cache_service, test_config):
    """Test cache cleanup with error."""
    # Start service
    await cache_service.start()
    
    # Create cache entry that raises error on cleanup
    entry = CacheEntry(test_config)
    entry.is_expired = MagicMock(side_effect=Exception("Cleanup error"))
    cache_service._cache["test"] = entry
    
    # Run cleanup
    await cache_service._cleanup_cache()
    
    # Verify service continues running despite error
    assert cache_service.is_running
    assert "test" in cache_service._cache
