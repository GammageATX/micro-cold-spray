"""Test configuration service."""

import threading
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import asyncio

from micro_cold_spray.api.base.base_errors import ConfigError
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.models import ConfigData
from micro_cold_spray.api.config.utils.config_singleton import cleanup_config_service, get_config_service


@pytest.fixture
async def config_service():
    """Create a config service instance."""
    cleanup_config_service()  # Ensure clean state
    service = ConfigService(service_name="config")
    yield service
    # Cleanup after each test
    await service.stop()
    cleanup_config_service()


@pytest.mark.asyncio
async def test_health_check(config_service):
    """Test health check."""
    # Start service
    await config_service.start()
    
    # Check health
    health = await config_service.check_health()
    assert health["status"] == "ok"
    assert health["service_info"]["config_types"] == []


@pytest.mark.asyncio
async def test_service_lifecycle(config_service):
    """Test service lifecycle."""
    # Start service
    await config_service.start()
    assert config_service.is_running
    
    # Stop service
    await config_service.stop()
    assert not config_service.is_running


@pytest.mark.asyncio
async def test_get_config(config_service):
    """Test getting configuration."""
    # Register config type
    config_service.register_config_type(ConfigData)
    
    # Get config type
    config_type = config_service.get_config_type("ConfigData")
    assert config_type == ConfigData


@pytest.mark.asyncio
async def test_update_config(config_service):
    """Test updating configuration."""
    # Start service
    await config_service.start()
    
    # Create test config type
    class TestConfig(ConfigData):
        pass
    
    # Register config type
    config_service.register_config_type(TestConfig)
    
    # Update config
    config = TestConfig(
        metadata={
            "config_type": "TestConfig",  # Must match class name
            "version": "1.0.0",
            "last_modified": datetime.now().isoformat()
        },
        data={
            "test_key": "test_value"
        }
    )
    await config_service.update_config(config)
    
    # Verify config was updated
    stored_config = await config_service.get_config("TestConfig")
    assert stored_config == config


@pytest.mark.asyncio
async def test_clear_cache(config_service):
    """Test clearing configuration cache."""
    # Start service
    await config_service.start()
    
    # Create test config type
    class TestConfig(ConfigData):
        pass
    
    # Register config type
    config_service.register_config_type(TestConfig)
    
    # Update config
    config = TestConfig(
        metadata={
            "config_type": "TestConfig",  # Must match class name
            "version": "1.0.0",
            "last_modified": datetime.now().isoformat()
        },
        data={
            "test_key": "test_value"
        }
    )
    await config_service.update_config(config)
    
    # Clear cache
    await config_service.clear_cache()
    
    # Verify config was cleared
    with pytest.raises(ConfigError):
        await config_service.get_config("TestConfig")


@pytest.mark.asyncio
async def test_concurrent_operations(config_service):
    """Test concurrent operations."""
    # Start service
    await config_service.start()
    
    # Create test config types
    test_configs = []
    for i in range(10):
        class_name = f"TestConfig{i}"
        TestConfig = type(class_name, (ConfigData,), {})
        config_service.register_config_type(TestConfig)
        
        config = TestConfig(
            metadata={
                "config_type": class_name,  # Must match class name
                "version": "1.0.0",
                "last_modified": datetime.now().isoformat()
            },
            data={
                "test_key": f"test_value_{i}"
            }
        )
        test_configs.append((class_name, config))
    
    # Create multiple tasks to update config
    tasks = []
    for _, config in test_configs:
        task = config_service.update_config(config)
        tasks.append(task)
    
    # Wait for all tasks to complete
    await asyncio.gather(*tasks)
    
    # Verify all configs were updated
    for class_name, config in test_configs:
        stored_config = await config_service.get_config(class_name)
        assert stored_config.data["test_key"] == config.data["test_key"]


@pytest.mark.asyncio
async def test_thread_safety():
    """Test thread safety of ConfigService singleton."""
    # Reset singleton state
    cleanup_config_service()
    
    async def create_service():
        """Create service instance."""
        service = get_config_service()
        await service.start()
        return service
    
    # Create multiple instances concurrently
    tasks = []
    instances = []
    
    for _ in range(10):
        task = create_service()
        tasks.append(task)
    
    # Wait for all tasks and collect instances
    results = await asyncio.gather(*tasks)
    instances.extend(results)
    
    # Verify all instances are the same object
    first_instance = instances[0]
    for instance in instances[1:]:
        assert instance is first_instance
    
    # Cleanup
    await first_instance.stop()
    cleanup_config_service()
