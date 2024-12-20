"""Configuration service tests."""

import pytest
from typing import AsyncGenerator
from fastapi import status
from unittest.mock import AsyncMock, patch

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config.config_service import ConfigService
from tests.test_config.conftest import BaseConfigTest, TestConfigData


class TestConfigService(BaseConfigTest):
    """Configuration service tests."""

    @pytest.fixture
    async def config_service(self) -> AsyncGenerator[ConfigService, None]:
        """Create config service fixture."""
        service = ConfigService()
        await service.start()
        yield service
        await service.stop()

    async def test_service_lifecycle(self, config_service: ConfigService):
        """Test service lifecycle."""
        assert config_service.is_running
        await config_service.stop()
        assert not config_service.is_running

    async def test_service_start_error(self):
        """Test service start error."""
        service = ConfigService()
        with patch.object(service._registry, "start") as mock_start:
            mock_start.side_effect = Exception("Start failed")
            with pytest.raises(Exception) as exc:
                await service.start()
            assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    async def test_service_stop_error(self):
        """Test service stop error."""
        service = ConfigService()
        await service.start()
        with patch.object(service._registry, "stop") as mock_stop:
            mock_stop.side_effect = Exception("Stop failed")
            with pytest.raises(Exception) as exc:
                await service.stop()
            assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    async def test_get_config_service_not_running(self, config_service: ConfigService):
        """Test getting config when service not running."""
        await config_service.stop()
        with pytest.raises(Exception) as exc:
            await config_service.get_config("test")
        assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    async def test_register_config_type(self, config_service: ConfigService):
        """Test registering config type."""
        await config_service.register_config_type(TestConfigData)
        config_type = await config_service._registry.get_config_type(TestConfigData.__name__)
        assert config_type == TestConfigData

    async def test_register_duplicate_config_type(self, config_service: ConfigService):
        """Test registering duplicate config type."""
        await config_service.register_config_type(TestConfigData)
        with pytest.raises(Exception) as exc:
            await config_service.register_config_type(TestConfigData)
        assert exc.value.status_code == status.HTTP_409_CONFLICT

    async def test_health_check(self, config_service: ConfigService):
        """Test health check."""
        await self.verify_service_health(config_service)

    async def test_health_check_error(self, config_service: ConfigService):
        """Test health check with error."""
        await config_service.stop()
        await self.verify_service_health(config_service, expected_healthy=False)
