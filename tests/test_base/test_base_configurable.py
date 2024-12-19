"""Test base configurable functionality."""

import pytest
from typing import Optional, AsyncGenerator
from pydantic import BaseModel

from micro_cold_spray.api.base import BaseService
from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_errors import ConfigError


class MockConfig(BaseModel):
    """Mock configuration model for testing."""
    required_field: str
    number_field: Optional[int] = None


class MockConfigurableService(ConfigurableService):
    """Mock configurable service for testing."""

    def __init__(self, service_name: str = "test_service"):
        """Initialize mock service."""
        super().__init__(service_name, MockConfig)
        self._mock_start_called = False
        self._mock_stop_called = False

    async def _start(self) -> None:
        """Start implementation."""
        self._mock_start_called = True

    async def _stop(self) -> None:
        """Stop implementation."""
        self._mock_stop_called = True

    async def _validate_config(self, config: MockConfig) -> None:
        """Validate configuration."""
        if config.number_field is not None and config.number_field < 0:
            raise ConfigError("Number field must be non-negative")


class TestConfigurableService:
    """Test configurable service functionality."""

    @pytest.fixture
    async def service(self) -> AsyncGenerator[MockConfigurableService, None]:
        """Create mock configurable service."""
        service = MockConfigurableService()
        yield service
        if service.is_running:
            await service.stop()

    @pytest.mark.asyncio
    async def test_configure_success(self, service):
        """Test successful configuration."""
        config = {
            "required_field": "test",
            "number_field": 42
        }
        await service.configure(config)
        assert service.is_configured
        assert service.config.required_field == "test"
        assert service.config.number_field == 42

    @pytest.mark.asyncio
    async def test_configure_minimal(self, service):
        """Test minimal configuration."""
        config = {
            "required_field": "test"
        }
        await service.configure(config)
        assert service.is_configured
        assert service.config.required_field == "test"
        assert service.config.number_field is None

    @pytest.mark.asyncio
    async def test_configure_invalid_type(self, service):
        """Test configuration with invalid type."""
        with pytest.raises(ConfigError) as exc:
            await service.configure({"required_field": 123})
        assert "validation error" in str(exc.value)
        assert not service.is_configured

    @pytest.mark.asyncio
    async def test_configure_missing_required(self, service):
        """Test configuration with missing required field."""
        with pytest.raises(ConfigError) as exc:
            await service.configure({})
        assert "validation error" in str(exc.value)
        assert not service.is_configured

    @pytest.mark.asyncio
    async def test_configure_invalid_value(self, service):
        """Test configuration with invalid value."""
        with pytest.raises(ConfigError) as exc:
            await service.configure({
                "required_field": "test",
                "number_field": -1
            })
        assert "Number field must be non-negative" in str(exc.value)
        assert not service.is_configured

    @pytest.mark.asyncio
    async def test_start_unconfigured(self, service):
        """Test starting unconfigured service."""
        with pytest.raises(ConfigError) as exc:
            await service.start()
        assert "Service must be configured before starting" in str(exc.value)
        assert not service.is_running

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test health check with configuration."""
        config = {
            "required_field": "test",
            "number_field": 42
        }
        await service.configure(config)
        await service.start()
        health = await service.check_health()
        assert health["status"] == "ok"
        assert health["service_info"]["name"] == "test_service"
        assert health["service_info"]["running"] is True
        assert isinstance(health["service_info"]["uptime"], str)
        assert "metrics" in health["service_info"]
