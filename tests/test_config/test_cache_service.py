"""Tests for config cache service."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import asyncio

from micro_cold_spray.api.config.services.cache_service import ConfigCacheService, CacheEntry
from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata
from micro_cold_spray.api.base.exceptions import ConfigurationError
from micro_cold_spray.api.base import BaseService


@pytest.fixture
def cache_service():
    """Create cache service."""
    return ConfigCacheService()


@pytest.mark.asyncio
async def test_service_start_stop(cache_service):
    """Test service startup and shutdown."""
    # Start service
    await cache_service.start()
    assert cache_service.is_running
    assert len(cache_service._cache) == 0
    
    # Stop service
    await cache_service.stop()
    assert not cache_service.is_running
    assert len(cache_service._cache) == 0


@pytest.mark.asyncio
async def test_service_start_error():
    """Test service startup with error."""
    service = ConfigCacheService()
    
    # Mock start to raise an error
    with patch.object(BaseService, 'start', side_effect=ConfigurationError("Start error")):
        with pytest.raises(ConfigurationError) as exc_info:
            await service.start()
        assert "Start error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_service_stop_error():
    """Test service shutdown with error."""
    service = ConfigCacheService()
    await service.start()
    
    # Mock stop to raise an error
    with patch.object(BaseService, 'stop', side_effect=ConfigurationError("Stop error")):
        with pytest.raises(ConfigurationError) as exc_info:
            await service.stop()
        assert "Stop error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cache_entry_validation():
    """Test cache entry validation."""
    # Create valid config first
    valid_config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now(),
            version="1.0.0"
        ),
        data={"key": "value"}
    )
    
    # Test with None config
    with pytest.raises(ValueError, match="Config data cannot be None"):
        CacheEntry(None)
    
    # Test with invalid data
    invalid_config = valid_config.model_copy()
    invalid_config.data = None
    with pytest.raises(ValueError, match="Invalid config data"):
        CacheEntry(invalid_config)


@pytest.mark.asyncio
async def test_cache_config(cache_service):
    """Test caching configuration."""
    # Start service
    await cache_service.start()
    
    # Create test config
    config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now(),
            version="1.0.0"
        ),
        data={"key": "value"}
    )
    
    # Cache config
    await cache_service.cache_config("test", config)
    
    # Verify config was cached
    cached = await cache_service.get_cached_config("test")
    assert cached == config
    
    # Verify cache entry
    assert "test" in cache_service._cache
    assert isinstance(cache_service._cache["test"], CacheEntry)
    assert cache_service._cache["test"].data == config


@pytest.mark.asyncio
async def test_get_cached_config_missing(cache_service):
    """Test getting non-existent cached config."""
    # Start service
    await cache_service.start()
    
    # Get non-existent config
    cached = await cache_service.get_cached_config("nonexistent")
    assert cached is None


@pytest.mark.asyncio
async def test_get_cached_config_expired(cache_service):
    """Test getting expired cached config."""
    # Start service
    await cache_service.start()
    
    # Create test config
    config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now(),
            version="1.0.0"
        ),
        data={"key": "value"}
    )
    
    # Create expired cache entry
    entry = CacheEntry(config, ttl=1)  # 1 second TTL
    entry.timestamp = datetime.now() - timedelta(seconds=2)  # Make it expired
    cache_service._cache["test"] = entry
    
    # Get expired config
    cached = await cache_service.get_cached_config("test")
    assert cached is None


@pytest.mark.asyncio
async def test_remove_from_cache(cache_service):
    """Test removing cached config."""
    # Start service
    await cache_service.start()
    
    # Create test config
    config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now(),
            version="1.0.0"
        ),
        data={"key": "value"}
    )
    
    # Create cache entry
    entry = CacheEntry(config)
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
async def test_clear_cache(cache_service):
    """Test clearing entire cache."""
    # Start service
    await cache_service.start()
    
    # Create test configs
    configs = {
        "test1": ConfigData(
            metadata=ConfigMetadata(
                config_type="test1",
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={"key1": "value1"}
        ),
        "test2": ConfigData(
            metadata=ConfigMetadata(
                config_type="test2",
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={"key2": "value2"}
        )
    }
    
    # Create cache entries
    for config_type, config in configs.items():
        entry = CacheEntry(config)
        cache_service._cache[config_type] = entry
    
    # Clear cache
    await cache_service.clear_cache()
    
    # Verify all configs were removed
    assert len(cache_service._cache) == 0
    for config_type in configs:
        cached = await cache_service.get_cached_config(config_type)
        assert cached is None


@pytest.mark.asyncio
async def test_cache_config_update(cache_service):
    """Test updating cached config."""
    # Start service
    await cache_service.start()
    
    # Create initial config
    initial_config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now(),
            version="1.0.0"
        ),
        data={"key": "value1"}
    )
    
    # Create initial cache entry
    initial_entry = CacheEntry(initial_config)
    cache_service._cache["test"] = initial_entry
    
    # Create updated config
    updated_config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now(),
            version="1.0.0"
        ),
        data={"key": "value2"}
    )
    
    # Cache updated config
    await cache_service.cache_config("test", updated_config)
    
    # Verify config was updated
    cached = await cache_service.get_cached_config("test")
    assert cached == updated_config
    assert cached.data["key"] == "value2"
    
    # Verify cache entry was updated
    assert isinstance(cache_service._cache["test"], CacheEntry)
    assert cache_service._cache["test"].data == updated_config


@pytest.mark.asyncio
async def test_cache_config_invalid(cache_service):
    """Test caching invalid config."""
    # Start service
    await cache_service.start()
    
    # Try to cache None config
    with pytest.raises(ConfigurationError, match="Config data cannot be None"):
        await cache_service.cache_config("test", None)
    
    # Try to cache with None type
    with pytest.raises(ConfigurationError, match="Config type cannot be None"):
        await cache_service.cache_config(None, ConfigData(
            metadata=ConfigMetadata(
                config_type="test",
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={"key": "value"}
        ))


@pytest.mark.asyncio
async def test_get_cached_config_invalid(cache_service):
    """Test getting cached config with invalid type."""
    # Start service
    await cache_service.start()
    
    # Try to get with None type
    with pytest.raises(ConfigurationError, match="Config type cannot be None"):
        await cache_service.get_cached_config(None)


@pytest.mark.asyncio
async def test_cache_size(cache_service):
    """Test getting cache size."""
    # Start service
    await cache_service.start()
    
    # Initially empty
    assert cache_service.cache_size == 0
    
    # Add some configs
    configs = {
        "test1": ConfigData(
            metadata=ConfigMetadata(
                config_type="test1",
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={"key1": "value1"}
        ),
        "test2": ConfigData(
            metadata=ConfigMetadata(
                config_type="test2",
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={"key2": "value2"}
        )
    }
    
    # Create cache entries
    for config_type, config in configs.items():
        entry = CacheEntry(config)
        cache_service._cache[config_type] = entry
    
    # Verify size
    assert cache_service.cache_size == 2
    
    # Remove one config
    await cache_service.remove_from_cache("test1")
    assert cache_service.cache_size == 1
    
    # Clear cache
    await cache_service.clear_cache()
    assert cache_service.cache_size == 0


@pytest.mark.asyncio
async def test_last_update(cache_service):
    """Test getting last update timestamp."""
    # Start service
    await cache_service.start()
    
    # Get initial timestamp
    initial_timestamp = cache_service.last_update
    assert initial_timestamp is not None
    
    # Wait a bit
    await asyncio.sleep(0.1)
    
    # Clear cache
    await cache_service.clear_cache()
    
    # Verify timestamp was updated
    assert cache_service.last_update > initial_timestamp


@pytest.mark.asyncio
async def test_cleanup_expired(cache_service):
    """Test cleanup of expired entries."""
    # Start service
    await cache_service.start()
    
    # Create test configs
    configs = {
        "test1": ConfigData(
            metadata=ConfigMetadata(
                config_type="test1",
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={"key1": "value1"}
        ),
        "test2": ConfigData(
            metadata=ConfigMetadata(
                config_type="test2",
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={"key2": "value2"}
        )
    }
    
    # Create cache entries with different TTLs
    entry1 = CacheEntry(configs["test1"], ttl=1)  # 1 second TTL
    entry1.timestamp = datetime.now() - timedelta(seconds=2)  # Make it expired
    cache_service._cache["test1"] = entry1
    
    entry2 = CacheEntry(configs["test2"], ttl=3600)  # 1 hour TTL
    cache_service._cache["test2"] = entry2
    
    # Force cleanup by setting last cleanup to old timestamp
    cache_service._last_cleanup = datetime.now() - timedelta(seconds=61)
    
    # Get any config to trigger cleanup
    await cache_service.get_cached_config("test1")
    
    # Verify expired entry was removed
    assert "test1" not in cache_service._cache
    assert "test2" in cache_service._cache
    
    # Verify cache size
    assert cache_service.cache_size == 1


@pytest.mark.asyncio
async def test_cache_config_error(cache_service):
    """Test caching config with error."""
    # Start service
    await cache_service.start()
    
    # Create test config that will raise error
    config = MagicMock()
    config.data = None  # This will cause a TypeError when creating CacheEntry
    config.metadata = None  # This will cause a TypeError when creating CacheEntry
    
    # Try to cache config
    with pytest.raises(ConfigurationError, match="Failed to cache config"):
        await cache_service.cache_config("test", config)
