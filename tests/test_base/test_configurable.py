"""Tests for configurable service functionality."""

import pytest
from unittest.mock import Mock, AsyncMock
from micro_cold_spray.api.base import ConfigurableService
from tests.test_config.helpers import load_yaml_file, create_test_config


@pytest.fixture
def mock_config_service():
    """Create a mock config service."""
    service = Mock()
    service.get_config = AsyncMock(return_value={})  # Default empty config
    return service


class TestConfigurableService:
    """Test configurable service functionality."""
    
    def test_init(self, mock_config_service):
        """Test configurable service initialization."""
        service = ConfigurableService("test_config", mock_config_service)
        assert service._config == {}
        assert service._config_service == mock_config_service
        assert service._config_type == "test_config"
        
    @pytest.mark.asyncio
    async def test_configure(self, tmp_path, mock_config_service):
        """Test configuration management."""
        service = ConfigurableService("test_config", mock_config_service)
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
    async def test_start_without_config(self, mock_config_service):
        """Test starting service without configuration."""
        service = ConfigurableService("test_config", mock_config_service)
        mock_config_service.get_config.side_effect = Exception("No config")
        
        await service.start()  # Should log warning but start
        assert service.is_running
        mock_config_service.get_config.assert_called_once_with("test_config")

    @pytest.mark.asyncio
    async def test_start_with_config(self, mock_config_service):
        """Test starting service with configuration."""
        service = ConfigurableService("test_config", mock_config_service)
        test_data = {"test": "value"}
        mock_config_service.get_config.return_value = test_data
        
        await service.start()
        assert service.is_running
        assert service.config == test_data
        mock_config_service.get_config.assert_called_once_with("test_config")

    @pytest.mark.asyncio
    async def test_start_config_error(self, mock_config_service):
        """Test starting service with config error."""
        service = ConfigurableService("test_config", mock_config_service)
        mock_config_service.get_config.side_effect = Exception("Config error")
        
        await service.start()  # Should log error but start
        assert service.is_running
        assert service.config == {}
        mock_config_service.get_config.assert_called_once_with("test_config")

    @pytest.mark.asyncio
    async def test_restart(self, mock_config_service):
        """Test service restart."""
        service = ConfigurableService("test_config", mock_config_service)
        test_data = {"test": "value"}
        mock_config_service.get_config.return_value = test_data
        
        await service.start()
        assert service.is_running
        assert service.config == test_data
        
        # Clear config and restart
        service._config = {}
        await service.restart()
        assert service.is_running
        assert service.config == test_data  # Should reload config
        assert mock_config_service.get_config.call_count == 2  # Called during start and restart

    def test_set_config_type(self, mock_config_service):
        """Test setting config type."""
        service = ConfigurableService("test_config", mock_config_service)
        service.set_config_type("new_config")
        assert service._config_type == "new_config"

    @pytest.mark.asyncio
    async def test_config_service_property(self, mock_config_service):
        """Test config service property."""
        service = ConfigurableService("test_config", mock_config_service)
        assert service.config_service == mock_config_service
