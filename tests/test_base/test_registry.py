"""Tests for service registry functionality."""

import pytest
from typing import Optional

from micro_cold_spray.api.base import (
    BaseService,
    ConfigurableService,
    get_service,
    register_service
)


class MockBaseService(BaseService):
    """Mock service for testing."""
    
    def __init__(self, service_name: str = "mock_base_service"):
        """Initialize mock service."""
        super().__init__(service_name)
        self._initialized = False
        self._running = False
        
    async def initialize(self) -> None:
        """Initialize the service."""
        self._initialized = True
        
    async def start(self) -> None:
        """Start the service."""
        self._running = True
        
    async def stop(self) -> None:
        """Stop the service."""
        self._running = False
        
    @property
    def is_running(self) -> bool:
        """Return running state."""
        return self._running


class MockConfigService(BaseService):
    """Mock config service for testing."""
    
    def __init__(self, service_name: str = "mock_config_service"):
        """Initialize mock config service."""
        super().__init__(service_name)
        self._config: Optional[dict] = None
        
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


class MockConfigurableService(ConfigurableService):
    """Mock configurable service for testing."""
    
    def __init__(self, service_name: str = "mock_configurable_service"):
        """Initialize mock configurable service."""
        config_service = MockConfigService()
        super().__init__(service_name, config_service)
        self._config: Optional[dict] = None
        
    async def configure(self, config: dict) -> None:
        """Configure the service."""
        self._config = config


class TestServiceRegistry:
    """Test service registry functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Clear service registry before each test
        from micro_cold_spray.api.base import _services
        _services.clear()
        
    def test_register_get_service(self):
        """Test registering and retrieving a service."""
        service = MockBaseService("test_service")
        register_service(service)
        
        # Get service using dependency function
        get_service_fn = get_service(MockBaseService)
        retrieved_service = get_service_fn()
        
        assert retrieved_service is service
        assert isinstance(retrieved_service, MockBaseService)
        
    def test_register_multiple_services(self):
        """Test registering multiple services."""
        base_service = MockBaseService("base_service")
        config_service = MockConfigurableService("config_service")
        
        register_service(base_service)
        register_service(config_service)
        
        # Get services using dependency functions
        get_base_fn = get_service(MockBaseService)
        get_config_fn = get_service(MockConfigurableService)
        
        assert get_base_fn() is base_service
        assert get_config_fn() is config_service
        
    def test_register_service_override(self):
        """Test overriding a registered service."""
        service1 = MockBaseService("service1")
        service2 = MockBaseService("service2")
        
        register_service(service1)
        register_service(service2)
        
        # Get service using dependency function
        get_service_fn = get_service(MockBaseService)
        retrieved_service = get_service_fn()
        
        assert retrieved_service is service2
        assert retrieved_service is not service1
        
    def test_unregistered_service(self):
        """Test getting an unregistered service."""
        with pytest.raises(RuntimeError) as exc_info:
            get_service_fn = get_service(MockBaseService)
            get_service_fn()
            
        assert "Service MockBaseService not initialized" in str(exc_info.value)
        
    def test_register_invalid_service(self):
        """Test registering an invalid service."""
        class InvalidService:
            pass
            
        with pytest.raises(TypeError) as exc_info:
            register_service(InvalidService())  # type: ignore
            
        assert "Service must be an instance of BaseService" in str(exc_info.value)
        
    def test_get_service_wrong_type(self):
        """Test getting a service with wrong type."""
        service = MockBaseService("test_service")
        register_service(service)
        
        with pytest.raises(RuntimeError) as exc_info:
            get_service_fn = get_service(MockConfigurableService)
            get_service_fn()
            
        assert "Service MockConfigurableService not initialized" in str(exc_info.value)
        
    def test_service_type_checking(self):
        """Test service type checking."""
        service = MockBaseService("test_service")
        register_service(service)
        
        # Get service with base type
        get_base_fn = get_service(BaseService)
        retrieved_service = get_base_fn()
        assert retrieved_service is service
        
        # Get service with specific type
        get_specific_fn = get_service(MockBaseService)
        retrieved_specific = get_specific_fn()
        assert retrieved_specific is service
        
        # Get service with wrong type
        with pytest.raises(RuntimeError):
            get_config_fn = get_service(ConfigurableService)
            get_config_fn()
