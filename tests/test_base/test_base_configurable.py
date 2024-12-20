"""Test base configurable module."""

import pytest
from pydantic import BaseModel, Field
from fastapi import HTTPException, status

from micro_cold_spray.api.base.base_configurable import ConfigurableService
from tests.conftest import MockBaseService


class ConfigModel(BaseModel):
    """Test configuration model."""
    value: int = Field(default=0, ge=0)
    name: str = Field(default="test")
    required_field: str


class ConfigurableTestService(MockBaseService, ConfigurableService[ConfigModel]):
    """Test configurable service."""
    def __init__(self):
        """Initialize test service."""
        MockBaseService.__init__(self)
        ConfigurableService.__init__(self, ConfigModel)


class TestConfigurable:
    """Test configurable service."""

    @pytest.mark.asyncio
    async def test_configure_valid(self):
        """Test configuring with valid data."""
        service = ConfigurableTestService()
        config = ConfigModel(value=123, name="test", required_field="test")
        await service.configure(config)
        assert service.config == config
        assert service.is_configured

    @pytest.mark.asyncio
    async def test_configure_dict(self):
        """Test configuring with dict data."""
        service = ConfigurableTestService()
        await service.configure({"value": 123, "name": "test", "required_field": "test"})
        assert service.config.value == 123
        assert service.config.name == "test"
        assert service.is_configured

    @pytest.mark.asyncio
    async def test_configure_invalid_value(self):
        """Test configuring with invalid value."""
        service = ConfigurableTestService()
        with pytest.raises(HTTPException) as exc:
            await service.configure({"value": -1, "required_field": "test"})
        assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Configuration validation failed" in str(exc.value.detail["message"])

    @pytest.mark.asyncio
    async def test_configure_invalid_type(self):
        """Test configuring with invalid type."""
        service = ConfigurableTestService()
        with pytest.raises(HTTPException) as exc:
            await service.configure({"value": "invalid", "required_field": "test"})
        assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Configuration validation failed" in str(exc.value.detail["message"])

    @pytest.mark.asyncio
    async def test_configure_missing_required(self):
        """Test configuring with missing required field."""
        service = ConfigurableTestService()
        with pytest.raises(HTTPException) as exc:
            await service.configure({})
        assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Configuration validation failed" in str(exc.value.detail["message"])

    @pytest.mark.asyncio
    async def test_configure_unexpected_error(self):
        """Test configuring with unexpected error."""
        service = ConfigurableTestService()
        with pytest.raises(HTTPException) as exc:
            await service.configure(None)
        assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid configuration type" in str(exc.value.detail["message"])

    @pytest.mark.asyncio
    async def test_is_configured(self):
        """Test is_configured property."""
        service = ConfigurableTestService()
        assert not service.is_configured
        await service.configure({"value": 123, "name": "test", "required_field": "test"})
        assert service.is_configured
