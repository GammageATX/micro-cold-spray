"""Tests for config cache service."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import asyncio

from micro_cold_spray.api.config.services.config_cache_service import ConfigCacheService, CacheEntry
from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata
from micro_cold_spray.api.base.base_exceptions import ConfigError

# Import base test utilities
from tests.test_config.config_test_base import test_service_lifecycle
# Import fixtures but don't redefine them
from tests.test_config.conftest import config_base_service  # noqa: F401
from tests.test_config.config_test_base import mock_service_error  # noqa: F401


@pytest.fixture
async def cache_service(config_base_service):
    """Create cache service.
    
    Args:
        config_base_service: Base config service fixture
    
    Returns:
        ConfigCacheService: Cache service instance
    """
    service = ConfigCacheService()
    await service.start()
    yield service
    await service.stop()


@pytest.mark.asyncio
async def test_service_lifecycle(cache_service):
    """Test service lifecycle using base pattern.
    
    Args:
        cache_service: Cache service fixture
    """
    await test_service_lifecycle(cache_service)


@pytest.mark.asyncio
async def test_service_start_error(mock_service_error):
    """Test service startup with error.
    
    Args:
        mock_service_error: Standard service error mock
    """
    service = ConfigCacheService()
    
    with patch.object(ConfigCacheService, 'start', side_effect=mock_service_error):
        with pytest.raises(ConfigError) as exc_info:
            await service.start()
        assert str(mock_service_error) in str(exc_info.value)


@pytest.mark.asyncio
async def test_service_stop_error(mock_service_error):
    """Test service shutdown with error.
    
    Args:
        mock_service_error: Standard service error mock
    """
    service = ConfigCacheService()
    await service.start()
    
    with patch.object(ConfigCacheService, 'stop', side_effect=mock_service_error):
        with pytest.raises(ConfigError) as exc_info:
            await service.stop()
        assert str(mock_service_error) in str(exc_info.value)


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
    cached = await cache_service.get_cached_config("nonexistent")
    assert cached is None


@pytest.mark.asyncio
async def test_get_cached_config_expired(cache_service):
    """Test getting expired cached config."""
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
async def test_cache_config_invalid(cache_service):
    """Test caching invalid config."""
    # Try to cache None config
    with pytest.raises(ConfigError, match="Config data cannot be None"):
        await cache_service.cache_config("test", None)
    
    # Try to cache with None type
    with pytest.raises(ConfigError, match="Config type cannot be None"):
        await cache_service.cache_config(None, ConfigData(
            metadata=ConfigMetadata(
                config_type="test",
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={"key": "value"}
        ))


@pytest.mark.asyncio
async def test_cache_config_error(cache_service):
    """Test caching config with error."""
    # Create test config that will raise error
    config = MagicMock()
    config.data = None  # This will cause a TypeError when creating CacheEntry
    config.metadata = None  # This will cause a TypeError when creating CacheEntry
    
    # Try to cache config
    with pytest.raises(ConfigError, match="Failed to cache config"):
        await cache_service.cache_config("test", config)
