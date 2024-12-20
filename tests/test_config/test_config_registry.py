"""Configuration registry service tests."""

import pytest
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config.services.registry_service import ConfigRegistryService
from tests.test_config.conftest import BaseConfigTest, TestConfigData


class TestConfigRegistry(BaseConfigTest):
    """Configuration registry service tests."""

    @pytest.fixture
    async def registry_service(self) -> ConfigRegistryService:
        """Create registry service fixture."""
        service = ConfigRegistryService()
        await service.start()
        yield service
        await service.stop()

    async def test_service_lifecycle(self, registry_service: ConfigRegistryService):
        """Test service lifecycle."""
        assert registry_service.is_running
        await registry_service.stop()
        assert not registry_service.is_running

    async def test_register_config_type(self, registry_service: ConfigRegistryService):
        """Test registering config type."""
        registry_service.register_config_type(TestConfigData)
        config_type = registry_service.get_config_type(TestConfigData.__name__)
        assert config_type == TestConfigData

    async def test_register_duplicate_config_type(self, registry_service: ConfigRegistryService):
        """Test registering duplicate config type."""
        registry_service.register_config_type(TestConfigData)
        with pytest.raises(Exception) as exc:
            registry_service.register_config_type(TestConfigData)
        assert exc.value.status_code == status.HTTP_409_CONFLICT

    async def test_get_config_type_not_found(self, registry_service: ConfigRegistryService):
        """Test getting nonexistent config type."""
        with pytest.raises(Exception) as exc:
            registry_service.get_config_type("nonexistent")
        assert exc.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_validate_references_valid(self, registry_service: ConfigRegistryService):
        """Test validating valid references."""
        data = {
            "tag": "test_tag",
            "action": "read",
            "validation": "range"
        }
        result = await registry_service.validate_references(data)
        assert result.valid
        assert not result.errors

    async def test_validate_references_invalid(self, registry_service: ConfigRegistryService):
        """Test validating invalid references."""
        data = {
            "tag": "invalid_tag",
            "action": "invalid_action",
            "validation": "invalid_validation"
        }
        result = await registry_service.validate_references(data)
        assert not result.valid
        assert len(result.errors) == 3

    async def test_health_check(self, registry_service: ConfigRegistryService):
        """Test health check."""
        await self.verify_service_health(registry_service)

    async def test_health_check_error(self, registry_service: ConfigRegistryService):
        """Test health check with error."""
        await registry_service.stop()
        await self.verify_service_health(registry_service, expected_healthy=False)
