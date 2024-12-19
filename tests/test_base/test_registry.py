"""Tests for service registry functionality."""

import pytest
from typing import Optional, List

from micro_cold_spray.api.base import (
    BaseService,
    ConfigurableService,
    get_service,
    register_service,
    get_service_by_name,
    clear_services
)
from micro_cold_spray.api.base.base_errors import ServiceError, AppErrorCode


class MockBaseService(BaseService):
    """Mock service for testing."""
    
    def __init__(
        self,
        service_name: str = "mock_base_service",
        dependencies: List[str] = None
    ):
        """Initialize mock service."""
        super().__init__(service_name, dependencies)
        self._initialized = False
        self._running = False
        self.start_order = []
        
    async def _start(self) -> None:
        """Start the service."""
        for dep in self.dependencies:
            try:
                dep_service = get_service_by_name(dep)
                if not dep_service.is_running:
                    raise ServiceError(
                        f"Dependency {dep} not running",
                        error_code=AppErrorCode.SERVICE_ERROR
                    )
                self.start_order.append(dep)
            except ServiceError as e:
                if e.error_code == AppErrorCode.SERVICE_NOT_FOUND:
                    raise ServiceError(
                        f"Dependency {dep} not running",
                        error_code=AppErrorCode.SERVICE_ERROR
                    ) from e
                raise
                
        self._running = True
        self.start_order.append(self._service_name)
        
    async def _stop(self) -> None:
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
        
    async def _start(self) -> None:
        """Start the service."""
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop the service."""
        self._is_running = False


class TestServiceRegistry:
    """Test service registry functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Clear service registry before each test
        clear_services()
        
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
        config_service = MockConfigService("config_service")
        
        register_service(base_service)
        register_service(config_service)
        
        # Get services using dependency functions
        get_base_fn = get_service(MockBaseService)
        get_config_fn = get_service(MockConfigService)
        
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
            get_service_fn = get_service(MockConfigService)
            get_service_fn()
            
        assert "Service MockConfigService not initialized" in str(exc_info.value)
        
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
            
    @pytest.mark.asyncio(loop_scope="session")
    async def test_service_dependency_order(self):
        """Test service dependency initialization order."""
        # Create services with dependencies
        config_service = MockBaseService("config")
        data_service = MockBaseService("data", dependencies=["config"])
        process_service = MockBaseService("process", dependencies=["config", "data"])
        
        # Register services
        register_service(config_service)
        register_service(data_service)
        register_service(process_service)
        
        # Start services in correct order
        await config_service.start()
        await data_service.start()
        await process_service.start()
        
        # Verify start order
        assert process_service.start_order == ["config", "data", "process"]
        
    @pytest.mark.asyncio(loop_scope="session")
    async def test_service_dependency_not_running(self):
        """Test service start with dependency not running."""
        # Create services with dependencies
        config_service = MockBaseService("config")
        data_service = MockBaseService("data", dependencies=["config"])
        
        # Register services but don't start config
        register_service(config_service)
        register_service(data_service)
        
        # Try to start dependent service
        with pytest.raises(ServiceError) as exc:
            await data_service.start()
        assert "Dependency config not running" in str(exc.value)
        
    @pytest.mark.asyncio(loop_scope="session")
    async def test_service_dependency_cycle(self):
        """Test service dependency cycle detection."""
        # Create services with cyclic dependencies
        service_a = MockBaseService("service_a", dependencies=["service_b"])
        service_b = MockBaseService("service_b", dependencies=["service_a"])
        
        # Register services
        register_service(service_a)
        with pytest.raises(ServiceError) as exc:
            register_service(service_b)
        assert "Dependency cycle detected: service_b" in str(exc.value)
