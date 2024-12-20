"""Test base configurable module."""

import pytest
from fastapi import status
from pydantic import BaseModel, Field

from micro_cold_spray.api.base.base_configurable import ConfigurableService


class _TestConfig(BaseModel):
    """Test configuration model."""
    value: int = Field(ge=0)


class _TestService(ConfigurableService[_TestConfig]):
    """Test configurable service."""

    def __init__(self, name: str = None):
        """Initialize test service."""
        super().__init__(_TestConfig, name)

    async def _start(self) -> None:
        """Start the service."""
        self._is_running = True

    async def _stop(self) -> None:
        """Stop the service."""
        self._is_running = False


@pytest.fixture
def service():
    """Create test service."""
    return _TestService("test_service")


class TestConfigurableService:
    """Test configurable service."""

    def test_configure_valid(self, service):
        """Test valid configuration."""
        config = _TestConfig(value=42)
        service.configure(config)
        assert service.config == config
        assert service.config.value == 42

    def test_configure_dict(self, service):
        """Test configuration with dict."""
        service.configure({"value": 42})
        assert service.config.value == 42

    def test_configure_invalid_value(self, service):
        """Test invalid configuration value."""
        with pytest.raises(Exception) as exc:
            service.configure({"value": -1})
        assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "value" in str(exc.value.detail)

    def test_configure_invalid_type(self, service):
        """Test invalid configuration type."""
        with pytest.raises(Exception) as exc:
            service.configure("invalid")
        assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_configure_missing_required(self, service):
        """Test missing required configuration."""
        with pytest.raises(Exception) as exc:
            service.configure({})
        assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "required" in str(exc.value.detail)

    def test_is_configured(self, service):
        """Test is_configured property."""
        assert not service.is_configured
        service.configure({"value": 42})
        assert service.is_configured
