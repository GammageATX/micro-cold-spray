"""Test base configurable module."""

import pytest
from pydantic import BaseModel, Field
from fastapi import status

from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_service import BaseService


class TestConfig(BaseModel):
    """Test configuration model."""
    value: int = Field(ge=0)
    name: str = Field(default="test")
    required_field: str


class TestConfigurableService(BaseService, ConfigurableService[TestConfig]):
    """Test configurable service implementation."""
    
    def __init__(self, name: str = None):
        """Initialize test service."""
        BaseService.__init__(self, name)
        ConfigurableService.__init__(self, TestConfig)
        
    async def _start(self) -> None:
        """Start implementation."""
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop implementation."""
        self._is_running = False


class TestConfigurable:
    """Test configurable service."""

    @pytest.mark.asyncio
    async def test_configure_valid_dict(self):
        """Test configuring with valid dictionary."""
        service = TestConfigurableService()
        config_data = {
            "value": 123,
            "name": "test",
            "required_field": "test"
        }
        await service.configure(config_data)
        assert service.config.value == 123
        assert service.config.name == "test"
        assert service.config.required_field == "test"
        assert service.is_configured

    @pytest.mark.asyncio
    async def test_configure_valid_model(self):
        """Test configuring with valid model."""
        service = TestConfigurableService()
        config = TestConfig(value=123, name="test", required_field="test")
        await service.configure(config)
        assert service.config == config
        assert service.is_configured

    @pytest.mark.asyncio
    async def test_configure_invalid_value(self):
        """Test configuring with invalid value."""
        service = TestConfigurableService()
        with pytest.raises(Exception) as exc:
            await service.configure({"value": -1, "required_field": "test"})
        assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "validation failed" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == service.name
        assert len(exc.value.detail["context"]["errors"]) > 0

    @pytest.mark.asyncio
    async def test_configure_missing_required(self):
        """Test configuring with missing required field."""
        service = TestConfigurableService()
        with pytest.raises(Exception) as exc:
            await service.configure({"value": 123})
        assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "validation failed" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == service.name
        assert len(exc.value.detail["context"]["errors"]) > 0

    @pytest.mark.asyncio
    async def test_configure_invalid_type(self):
        """Test configuring with invalid type."""
        service = TestConfigurableService()
        with pytest.raises(Exception) as exc:
            await service.configure(["not", "a", "dict"])
        assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid configuration type" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == service.name
        assert exc.value.detail["context"]["expected"] == "TestConfig"

    @pytest.mark.asyncio
    async def test_configure_while_running(self):
        """Test configuring while service is running."""
        service = TestConfigurableService()
        await service.start()
        with pytest.raises(Exception) as exc:
            await service.configure({"value": 123, "required_field": "test"})
        assert exc.value.status_code == status.HTTP_409_CONFLICT
        assert "Cannot configure while service is running" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == service.name

    @pytest.mark.asyncio
    async def test_config_not_configured(self):
        """Test accessing config when not configured."""
        service = TestConfigurableService()
        with pytest.raises(Exception) as exc:
            _ = service.config
        assert exc.value.status_code == status.HTTP_409_CONFLICT
        assert "Service is not configured" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == service.name

    @pytest.mark.asyncio
    async def test_is_configured(self):
        """Test is_configured property."""
        service = TestConfigurableService()
        assert not service.is_configured
        await service.configure({"value": 123, "required_field": "test"})
        assert service.is_configured

    @pytest.mark.asyncio
    async def test_inheritance_error(self):
        """Test using ConfigurableService without BaseService."""
        class InvalidService(ConfigurableService[TestConfig]):
            def __init__(self):
                super().__init__(TestConfig)

        service = InvalidService()
        with pytest.raises(Exception) as exc:
            await service.configure({"value": 123, "required_field": "test"})
        assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "must be used with BaseService" in str(exc.value.detail["message"])
