"""Tests for configurable service functionality."""

import pytest
from typing import Dict, Any
from micro_cold_spray.api.base import ConfigurableService, BaseService


class MockConfigService(BaseService):
    """Mock config service for testing."""
    
    def __init__(self, service_name: str = "mock_config_service"):
        """Initialize mock config service."""
        super().__init__(service_name)
        self._configs: Dict[str, dict] = {}
        self._should_raise = False
        
    async def initialize(self) -> None:
        """Initialize the service."""
        pass
        
    async def start(self) -> None:
        """Start the service."""
        pass
        
    async def stop(self) -> None:
        """Stop the service."""
        pass
        
    @property
    def is_running(self) -> bool:
        """Return running state."""
        return True
        
    async def get_config(self, config_type: str) -> dict:
        """Get configuration."""
        if self._should_raise:
            raise ValueError("Config error")
        return self._configs.get(config_type, {})
        
    def set_config(self, config_type: str, config: dict) -> None:
        """Set configuration."""
        self._configs[config_type] = config
        
    def set_should_raise(self, value: bool) -> None:
        """Set whether get_config should raise an error."""
        self._should_raise = value


class MockConfigurableService(ConfigurableService):
    """Mock configurable service for testing."""
    
    def __init__(self, service_name: str = "mock_configurable_service"):
        """Initialize mock configurable service."""
        self._config_service = MockConfigService()
        super().__init__(service_name, self._config_service)
        self._config: Dict[str, Any] = {}  # Initialize as empty dict
        
    async def configure(self, config: dict) -> None:
        """Configure the service."""
        self._config = config.copy()  # Make a copy to prevent modification
        self._config_service.set_config(self._config_type, config)  # Store config in service


class ErrorInStartConfigurableService(ConfigurableService):
    """Service that raises error in start."""
    
    def __init__(self, service_name: str = "error_start_service"):
        """Initialize service."""
        config_service = MockConfigService()
        super().__init__(service_name, config_service)
        
    async def _start(self) -> None:
        """Raise error during start."""
        raise ValueError("Start error")


class ErrorInConfigureService(ConfigurableService):
    """Service that raises error during configuration."""
    
    def __init__(self, service_name: str = "error_configure_service"):
        """Initialize service."""
        config_service = MockConfigService()
        super().__init__(service_name, config_service)
        
    async def configure(self, config: dict) -> None:
        """Raise error during configuration."""
        raise ValueError("Configure error")


class TestConfigurableService:
    """Test configurable service functionality."""
    
    def test_init(self):
        """Test service initialization."""
        config_service = MockConfigService()
        service = ConfigurableService("test_service", config_service)
        assert service._service_name == "test_service"
        assert service._config_service is config_service
        assert service._config_type == "test_service"  # Config type defaults to service name
        
    @pytest.mark.asyncio
    async def test_configure(self):
        """Test service configuration."""
        service = MockConfigurableService()
        config = {"key": "value"}
        await service.configure(config)
        assert service._config == config
        
    @pytest.mark.asyncio
    async def test_start_without_config(self):
        """Test starting service without configuration."""
        service = MockConfigurableService()
        await service.start()  # Should log warning but start
        assert service.is_running
        assert service._config == {}  # Should have empty config
            
    @pytest.mark.asyncio
    async def test_start_with_config(self):
        """Test starting service with configuration."""
        service = MockConfigurableService()
        config = {"key": "value"}
        await service.configure(config)
        await service.start()
        assert service.is_running
        
    @pytest.mark.asyncio
    async def test_start_config_error(self):
        """Test starting service with configuration error."""
        service = ErrorInConfigureService()
        config = {"key": "value"}
        
        with pytest.raises(ValueError, match="Configure error"):
            await service.configure(config)
            
    @pytest.mark.asyncio
    async def test_restart(self):
        """Test service restart."""
        service = MockConfigurableService()
        config = {"key": "value"}
        await service.configure(config)
        await service.start()
        assert service.is_running
        
        await service.restart()
        assert service.is_running
        assert service._config == config  # Config should persist after restart
        
    def test_set_config_type(self):
        """Test setting config type."""
        service = MockConfigurableService()
        config_type = "custom_config_type"
        service.set_config_type(config_type)
        assert service._config_type == config_type
        
    def test_config_service_property(self):
        """Test config service property."""
        config_service = MockConfigService()
        service = ConfigurableService("test_service", config_service)
        assert service.config_service is config_service

    @pytest.mark.asyncio
    async def test_start_implementation_error(self):
        """Test start with implementation error."""
        service = ErrorInStartConfigurableService()
        config = {"key": "value"}
        await service.configure(config)
        
        with pytest.raises(ValueError, match="Start error"):
            await service.start()
        assert service._error == "Start error"

    @pytest.mark.asyncio
    async def test_start_config_load_error(self):
        """Test starting service with config loading error."""
        service = MockConfigurableService()
        service._config_service.set_should_raise(True)  # Make get_config raise an error
        
        await service.start()  # Should log warning but start
        assert service.is_running
        assert service._config == {}  # Should have empty config

    @pytest.mark.asyncio
    async def test_start_with_config_type(self):
        """Test starting service with specific config type."""
        service = MockConfigurableService()
        service.set_config_type("custom_config")
        config = {"key": "value"}
        service._config_service.set_config("custom_config", config)
        
        await service.start()
        assert service.is_running
        assert service._config == config  # Should load config from service

    @pytest.mark.asyncio
    async def test_empty_config_handling(self):
        """Test handling of empty configuration."""
        service = MockConfigurableService()
        await service.configure({})  # Configure with empty dict
        await service.start()
        assert service.is_running
        assert service._config == {}

    @pytest.mark.asyncio
    async def test_config_persistence(self):
        """Test configuration persistence across service lifecycle."""
        service = MockConfigurableService()
        config = {"key": "value"}
        
        # Configure and start
        await service.configure(config)
        await service.start()
        assert service._config == config
        
        # Stop and restart
        await service.stop()
        await service.start()
        assert service._config == config  # Config should persist
        
        # Restart directly
        await service.restart()
        assert service._config == config  # Config should still persist

    @pytest.mark.asyncio
    async def test_invalid_config_type(self):
        """Test handling of invalid configuration type."""
        service = MockConfigurableService()
        service.set_config_type("invalid_type")  # Set a type that doesn't exist
        
        await service.start()  # Should start with empty config
        assert service.is_running
        assert service._config == {}

    def test_type_checking_import(self):
        """Test type checking import handling."""
        # This test verifies that the TYPE_CHECKING import works correctly
        # by checking that ConfigService type hint is properly resolved
        from micro_cold_spray.api.base.configurable import ConfigurableService
        
        # Get the type annotation directly from the __annotations__ dictionary
        annotations = ConfigurableService.__init__.__annotations__
        
        # Verify that config_service parameter has the correct type
        assert 'config_service' in annotations
        assert 'ConfigService' in str(annotations['config_service'])
