"""Tests for configuration registry service."""

import pytest
from datetime import datetime

from micro_cold_spray.api.base.base_errors import ConfigError
from micro_cold_spray.api.config.models.config_models import ConfigData, ConfigMetadata
from micro_cold_spray.api.config.services.config_registry_service import ConfigRegistryService


class TestConfigData(ConfigData):
    """Test configuration data."""
    data: dict = {"value": "test"}


@pytest.fixture
def registry_service():
    """Create registry service fixture."""
    service = ConfigRegistryService("registry")
    return service


@pytest.mark.asyncio
async def test_service_lifecycle(registry_service):
    """Test service lifecycle."""
    assert not registry_service.is_running
    await registry_service.start()
    assert registry_service.is_running
    await registry_service.stop()
    assert not registry_service.is_running


@pytest.mark.asyncio
async def test_register_config_type(registry_service):
    """Test registering config type."""
    await registry_service.start()
    registry_service.register_config_type(TestConfigData)
    assert "TestConfigData" in registry_service.get_config_types()


@pytest.mark.asyncio
async def test_register_duplicate_config_type(registry_service):
    """Test registering duplicate config type."""
    await registry_service.start()
    registry_service.register_config_type(TestConfigData)
    with pytest.raises(ConfigError):
        registry_service.register_config_type(TestConfigData)


@pytest.mark.asyncio
async def test_get_config_type(registry_service):
    """Test getting config type."""
    await registry_service.start()
    registry_service.register_config_type(TestConfigData)
    config_type = registry_service.get_config_type("TestConfigData")
    assert config_type == TestConfigData


@pytest.mark.asyncio
async def test_register_config(registry_service):
    """Test registering config."""
    await registry_service.start()
    registry_service.register_config_type(TestConfigData)
    
    config = TestConfigData(
        metadata=ConfigMetadata(
            config_type="TestConfigData",
            created=datetime.now(),
            last_modified=datetime.now()
        ),
        data={"value": "test"}
    )
    
    await registry_service.register_config(config)
    stored_config = await registry_service.get_config("TestConfigData")
    assert stored_config == config


@pytest.mark.asyncio
async def test_register_config_without_type(registry_service):
    """Test registering config without type."""
    await registry_service.start()
    config = TestConfigData(
        metadata=ConfigMetadata(
            config_type="",
            created=datetime.now(),
            last_modified=datetime.now()
        ),
        data={"value": "test"}
    )
    
    with pytest.raises(ConfigError):
        await registry_service.register_config(config)


@pytest.mark.asyncio
async def test_register_config_unregistered_type(registry_service):
    """Test registering config with unregistered type."""
    await registry_service.start()
    config = TestConfigData(
        metadata=ConfigMetadata(
            config_type="UnregisteredType",
            created=datetime.now(),
            last_modified=datetime.now()
        ),
        data={"value": "test"}
    )
    
    with pytest.raises(ConfigError):
        await registry_service.register_config(config)


@pytest.mark.asyncio
async def test_update_config(registry_service):
    """Test updating config."""
    await registry_service.start()
    registry_service.register_config_type(TestConfigData)
    
    config = TestConfigData(
        metadata=ConfigMetadata(
            config_type="TestConfigData",
            created=datetime.now(),
            last_modified=datetime.now()
        ),
        data={"value": "test"}
    )
    
    await registry_service.register_config(config)
    
    config.data["value"] = "updated"
    await registry_service.update_config(config)
    
    updated_config = await registry_service.get_config("TestConfigData")
    assert updated_config.data["value"] == "updated"


@pytest.mark.asyncio
async def test_delete_config(registry_service):
    """Test deleting config."""
    await registry_service.start()
    registry_service.register_config_type(TestConfigData)
    
    config = TestConfigData(
        metadata=ConfigMetadata(
            config_type="TestConfigData",
            created=datetime.now(),
            last_modified=datetime.now()
        ),
        data={"value": "test"}
    )
    
    await registry_service.register_config(config)
    await registry_service.delete_config("TestConfigData")
    
    assert await registry_service.get_config("TestConfigData") is None


@pytest.mark.asyncio
async def test_delete_nonexistent_config(registry_service):
    """Test deleting nonexistent config."""
    await registry_service.start()
    with pytest.raises(ConfigError):
        await registry_service.delete_config("NonexistentConfig")


@pytest.mark.asyncio
async def test_health_check(registry_service):
    """Test health check."""
    await registry_service.start()
    registry_service.register_config_type(TestConfigData)
    
    config = TestConfigData(
        metadata=ConfigMetadata(
            config_type="TestConfigData",
            created=datetime.now(),
            last_modified=datetime.now()
        ),
        data={"value": "test"}
    )
    
    await registry_service.register_config(config)
    
    health = await registry_service.check_health()
    assert health["is_healthy"]
    assert "TestConfigData" in health["service_info"]["config_types"]
    assert "TestConfigData" in health["service_info"]["configs"]
