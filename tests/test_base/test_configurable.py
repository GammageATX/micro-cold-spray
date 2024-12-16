"""Tests for configurable service functionality."""

import pytest
from micro_cold_spray.api.base import ConfigurableService
from tests.test_base.helpers import load_yaml_file, create_test_config


class TestConfigurableService:
    """Test configurable service functionality."""
    
    def test_init(self):
        """Test configurable service initialization."""
        service = ConfigurableService("test_config")
        assert service._config == {}
        
    @pytest.mark.asyncio
    async def test_configure(self, tmp_path):
        """Test configuration management."""
        service = ConfigurableService("test_config")
        test_data = {"test": "value"}
        test_config = create_test_config(tmp_path, "test_config", test_data)
        config_data = load_yaml_file(test_config)
        
        await service.configure(config_data)
        assert service.config == config_data
        assert service.config is not config_data  # Should be a copy
        
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
