"""Tests for configurable service functionality."""

import pytest
from micro_cold_spray.api.base import ConfigurableService
from tests.test_base.helpers import load_test_config


class TestConfigurableService:
    """Test configurable service functionality."""
    
    def test_init(self):
        """Test configurable service initialization."""
        service = ConfigurableService("test_config")
        assert service._config == {}
        
    @pytest.mark.asyncio
    async def test_configure(self):
        """Test configuration management."""
        service = ConfigurableService("test_config")
        test_config = load_test_config("test_config")
        
        await service.configure(test_config)
        assert service.config == test_config
        assert service.config is not test_config  # Should be a copy
        
        # Modify returned config
        config = service.config
        config["new_key"] = "new_value"
        assert "new_key" not in service._config  # Original should be unchanged

    @pytest.mark.asyncio
    async def test_start_without_config(self):
        """Test starting service without configuration."""
        service = ConfigurableService("test_config")
        await service.start()  # Should log warning but start
        assert service.is_running
