"""Tests for base router."""

import pytest
import os
import psutil
from unittest.mock import patch, Mock, AsyncMock
from fastapi import FastAPI, APIRouter, HTTPException
from micro_cold_spray.api.base.router import (
    add_health_endpoints,
    create_api_app,
    get_service_from_app,
)
from micro_cold_spray.api.base.service import BaseService
from micro_cold_spray.api.base.configurable import ConfigurableService
from micro_cold_spray.api.base.exceptions import ServiceError


class _MockServiceWithHealth(BaseService):
    """Mock service with health check capability for testing."""
    
    def __init__(self):
        """Initialize test service."""
        super().__init__("test_service")
        self._health_status = "ok"
        self._message = None
        self._error = None

    async def _check_health(self):
        if self._error:
            return {
                "status": "error",
                "error": self._error
            }
        return {
            "status": self._health_status,
            "message": self._message
        }

    def set_health_status(self, status, message=None):
        """Set health check response."""
        self._health_status = status
        self._message = message
        self._error = None

    def set_health_error(self, error):
        """Set health check to raise error."""
        self._error = error
        self._health_status = "error"
        self._message = None


@pytest.fixture
def mock_service_with_health():
    """Create mock service with health check capability."""
    return _MockServiceWithHealth()


@pytest.fixture
def test_router():
    """Create test router with service."""
    app = FastAPI()  # Create FastAPI app
    router = APIRouter()
    service = BaseService("test_service")
    
    # Add endpoints to router
    add_health_endpoints(router, service)
    
    # Include router in app
    app.include_router(router)
    
    return router, service


@pytest.fixture
def test_router_with_mock():
    """Create test router with mock service that has health check."""
    app = FastAPI()
    router = APIRouter()
    service = _MockServiceWithHealth()
    
    # Add endpoints to router
    add_health_endpoints(router, service)
    
    # Include router in app
    app.include_router(router)
    
    return router, service


@pytest.mark.asyncio
async def test_health_endpoint(test_router):
    """Test health check endpoint."""
    router, service = test_router
    
    # Start service
    await service.start()
    
    # Get route handler
    health_route = next(r for r in router.routes if r.path == "/health")
    response = await health_route.endpoint()
    
    assert response["status"] == "ok"
    assert "uptime" in response
    assert "memory_usage" in response
    assert response["service_info"]["name"] == "test_service"
    assert response["service_info"]["running"] is True
    assert response["service_info"]["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_health_check_error(test_router):
    """Test health check error handling."""
    router, service = test_router
    
    # Force error in _start to simulate health check error
    async def _start():
        raise ValueError("Test error")
    service._start = _start
    
    health_route = next(r for r in router.routes if r.path == "/health")
    
    # First verify the start() raises ValueError
    with pytest.raises(ValueError) as exc:
        await service.start()
    assert str(exc.value) == "Test error"
    
    # Then verify health check endpoint returns error status
    response = await health_route.endpoint()
    assert response["status"] == "error"
    assert response["error"] == "Service not initialized"
    assert response["service_info"]["error"] == "Service not initialized"
    assert response["service_info"]["running"] is False


@pytest.mark.asyncio
async def test_health_check_stopped(test_router):
    """Test health check when service is stopped."""
    router, service = test_router
    
    # Start service first so it's initialized
    await service.start()
    
    # Then stop service
    await service.stop()
    
    # Get route handler
    health_route = next(r for r in router.routes if r.path == "/health")
    response = await health_route.endpoint()
    
    assert response["status"] == "stopped"
    assert response["service_info"]["running"] is False
    assert response["service_info"]["uptime"] is None


@pytest.mark.asyncio
async def test_health_check_error_status(test_router_with_mock):
    """Test health check with error status."""
    router, service = test_router_with_mock
    
    # Start service
    await service.start()
    
    # Set error status
    service.set_health_error("Test error")
    
    # Get route handler
    health_route = next(r for r in router.routes if r.path == "/health")
    response = await health_route.endpoint()
    
    assert response["status"] == "error"
    assert response["error"] == "Test error"
    assert response["service_info"]["running"] is True


@pytest.mark.asyncio
async def test_health_check_degraded(test_router_with_mock):
    """Test health check with degraded status."""
    router, service = test_router_with_mock
    
    # Start service
    await service.start()
    
    # Set degraded status
    service.set_health_status("degraded", message="Performance degraded")
    
    # Get route handler
    health_route = next(r for r in router.routes if r.path == "/health")
    response = await health_route.endpoint()
    
    assert response["status"] == "degraded"
    assert response["message"] == "Performance degraded"
    assert response["service_info"]["running"] is True


@pytest.mark.asyncio
async def test_control_endpoint_restart(test_router):
    """Test control endpoint with restart action."""
    router, service = test_router
    
    # Get control route handler
    control_route = next(r for r in router.routes if r.path == "/control")
    
    # Test restart
    response = await control_route.endpoint(action="restart")
    assert response["status"] == "restarted"
    assert service.is_running


@pytest.mark.asyncio
async def test_control_endpoint_restart_error(test_router):
    """Test control endpoint with restart action error."""
    router, service = test_router
    
    # Force error in service start
    async def _start():
        raise ValueError("Start error")
    service._start = _start
    
    # Get control route handler
    control_route = next(r for r in router.routes if r.path == "/control")
    
    # Test restart error
    with pytest.raises(HTTPException) as exc:
        await control_route.endpoint(action="restart")
    assert exc.value.status_code == 500
    error_detail = exc.value.detail
    assert error_detail["code"] == "INTERNAL_ERROR"
    assert "Start error" in error_detail["message"]


@pytest.mark.asyncio
async def test_control_endpoint_invalid_action(test_router):
    """Test control endpoint with invalid action."""
    router, service = test_router
    
    # Get control route handler
    control_route = next(r for r in router.routes if r.path == "/control")
    
    # Test invalid action
    with pytest.raises(HTTPException) as exc:
        await control_route.endpoint(action="invalid")
    assert exc.value.status_code == 400
    error_detail = exc.value.detail
    assert error_detail["code"] == "INVALID_ACTION"
    assert "Invalid action: invalid" in error_detail["message"]
    assert error_detail["valid_actions"] == ["start", "stop", "restart"]


@pytest.mark.asyncio
async def test_control_endpoint_start(test_router):
    """Test control endpoint with start action."""
    router, service = test_router
    
    # Get control route handler
    control_route = next(r for r in router.routes if r.path == "/control")
    
    # Test start
    response = await control_route.endpoint(action="start")
    assert response["status"] == "started"
    assert service.is_running


@pytest.mark.asyncio
async def test_control_endpoint_stop(test_router):
    """Test control endpoint with stop action."""
    router, service = test_router
    
    # Start service first
    await service.start()
    assert service.is_running
    
    # Get control route handler
    control_route = next(r for r in router.routes if r.path == "/control")
    
    # Test stop
    response = await control_route.endpoint(action="stop")
    assert response["status"] == "stopped"
    assert not service.is_running


@pytest.mark.asyncio
async def test_control_endpoint_start_error(test_router):
    """Test control endpoint with start action error."""
    router, service = test_router
    
    # Force error in service start
    async def _start():
        raise ValueError("Start error")
    service._start = _start
    
    # Get control route handler
    control_route = next(r for r in router.routes if r.path == "/control")
    
    # Test start error
    with pytest.raises(HTTPException) as exc:
        await control_route.endpoint(action="start")
    assert exc.value.status_code == 500
    error_detail = exc.value.detail
    assert error_detail["code"] == "INTERNAL_ERROR"
    assert "Start error" in error_detail["message"]


@pytest.mark.asyncio
async def test_control_endpoint_stop_error(test_router):
    """Test control endpoint with stop action error."""
    router, service = test_router
    
    # Start service first
    await service.start()
    
    # Force error in service stop
    async def _stop():
        raise ValueError("Stop error")
    service._stop = _stop
    
    # Get control route handler
    control_route = next(r for r in router.routes if r.path == "/control")
    
    # Test stop error
    with pytest.raises(HTTPException) as exc:
        await control_route.endpoint(action="stop")
    assert exc.value.status_code == 500
    error_detail = exc.value.detail
    assert error_detail["code"] == "INTERNAL_ERROR"
    assert "Stop error" in error_detail["message"]


@pytest.mark.asyncio
async def test_health_check_with_service_error(test_router_with_mock):
    """Test health check when service raises error."""
    router, service = test_router_with_mock
    
    # Start service
    await service.start()
    
    # Force health check to raise error
    async def _check_health():
        raise ValueError("Health check error")
    service._check_health = _check_health
    
    # Get route handler
    health_route = next(r for r in router.routes if r.path == "/health")
    response = await health_route.endpoint()
    
    assert response["status"] == "error"
    assert "Health check error" in response["error"]
    assert response["service_info"]["running"] is True


@pytest.mark.asyncio
async def test_health_check_memory_error(test_router):
    """Test health check when memory info raises error."""
    router, service = test_router
    
    # Start service
    await service.start()
    
    # Mock psutil.Process to return a mock process
    class MockProcess:
        def __init__(self, *args, **kwargs):
            self.pid = os.getpid()
        
        def memory_info(self):
            raise psutil.AccessDenied(0)
        
        def cpu_percent(self):
            return 0.0
    
    with patch('psutil.Process', return_value=MockProcess()):
        # Get route handler
        health_route = next(r for r in router.routes if r.path == "/health")
        with pytest.raises(HTTPException) as exc:
            await health_route.endpoint()
        assert exc.value.status_code == 500
        error_detail = exc.value.detail
        assert error_detail["code"] == "HEALTH_CHECK_ERROR"


@pytest.mark.asyncio
async def test_health_check_custom_info(test_router_with_mock):
    """Test health check with custom service info."""
    router, service = test_router_with_mock
    
    # Start service
    await service.start()
    
    # Set custom health check response with custom fields at root level
    async def _check_health():
        return {
            "status": "ok",
            "custom_field": "test",
            "custom_info": "test",
            "service_info": {
                "name": service._service_name,
                "version": service.version,
                "running": service.is_running,
                "uptime": str(service.uptime)
            }
        }
    service._check_health = _check_health
    
    # Get route handler
    health_route = next(r for r in router.routes if r.path == "/health")
    response = await health_route.endpoint()
    
    assert response["status"] == "ok"
    assert response["custom_field"] == "test"
    assert response["custom_info"] == "test"
    assert response["service_info"]["name"] == service._service_name
    assert response["service_info"]["version"] == service.version
    assert response["service_info"]["running"] is True
    assert "uptime" in response["service_info"]
    assert "process_info" in response
    assert "memory_usage" in response


@pytest.mark.asyncio
async def test_health_check_service_error(test_router):
    """Test health check with service error."""
    router, service = test_router
    
    # Start service
    await service.start()
    
    # Force service error in check_health
    async def check_health():
        raise ServiceError("Service error")
    service.check_health = check_health
    
    # Get route handler
    health_route = next(r for r in router.routes if r.path == "/health")
    
    with pytest.raises(HTTPException) as exc:
        await health_route.endpoint()
    assert exc.value.status_code == 500
    error_detail = exc.value.detail
    assert error_detail["code"] == "HEALTH_CHECK_ERROR"
    assert "Service error" in error_detail["message"]


@pytest.mark.asyncio
async def test_control_endpoint_already_running(test_router):
    """Test control endpoint when service is already running."""
    router, service = test_router
    
    # Start service first
    await service.start()
    assert service.is_running
    
    # Get control route handler
    control_route = next(r for r in router.routes if r.path == "/control")
    
    # Test start when already running
    response = await control_route.endpoint(action="start")
    assert response["status"] == "started"
    assert service.is_running


@pytest.mark.asyncio
async def test_control_endpoint_already_stopped(test_router):
    """Test control endpoint when service is already stopped."""
    router, service = test_router
    
    # Get control route handler
    control_route = next(r for r in router.routes if r.path == "/control")
    
    # Test stop when already stopped
    response = await control_route.endpoint(action="stop")
    assert response["status"] == "stopped"
    assert not service.is_running


@pytest.mark.asyncio
async def test_create_api_app_base_service():
    """Test creating API app with base service."""
    router = APIRouter()
    
    class TestService(BaseService):
        def __init__(self):
            super().__init__("test_service")
    
    app = create_api_app(
        service_factory=TestService,
        prefix="/test",
        router=router
    )
    
    # Initialize app state
    app.state._state = {}
    
    # Test lifespan
    async with app.router.lifespan_context(app):
        # Service should be started
        assert isinstance(app.state.service, TestService)
        assert app.state.service.is_running
        assert app.state.service._service_name == "test_service"
    
    # Service should be stopped after context
    assert app.state._state.get("service") is None


@pytest.mark.asyncio
async def test_create_api_app_configurable_service():
    """Test creating API app with configurable service."""
    router = APIRouter()
    
    # Mock config service
    mock_config_service = Mock()
    mock_config_service.start = AsyncMock()
    mock_config_service.get_config = AsyncMock(return_value=Mock(data={"test": "value"}))
    
    class TestConfigurableService(ConfigurableService):
        def __init__(self, config_service):
            super().__init__("test_config_service", config_service)
    
    with patch('micro_cold_spray.api.config.singleton.get_config_service', return_value=mock_config_service):
        app = create_api_app(
            service_factory=TestConfigurableService,
            prefix="/test",
            router=router,
            config_type="test_config"
        )
        
        # Initialize app state
        app.state._state = {}
        
        # Test lifespan
        async with app.router.lifespan_context(app):
            # Config service should be started
            mock_config_service.start.assert_called_once()
            mock_config_service.get_config.assert_called_once_with("test_config")
            
            # Service should be started and configured
            assert isinstance(app.state.service, TestConfigurableService)
            assert app.state.service.is_running
            assert app.state.service._config_type == "test_config"
            assert app.state.service._config == {"test": "value"}
        
        # Service should be stopped after context
        assert app.state._state.get("service") is None


@pytest.mark.asyncio
async def test_create_api_app_with_additional_routers():
    """Test creating API app with additional routers."""
    main_router = APIRouter()
    additional_router = APIRouter()
    
    class TestService(BaseService):
        def __init__(self):
            super().__init__("test_service")
    
    @additional_router.get("/extra")
    def extra_endpoint():
        return {"status": "ok"}
    
    app = create_api_app(
        service_factory=TestService,
        prefix="/test",
        router=main_router,
        additional_routers=[additional_router]
    )
    
    # Initialize app state
    app.state._state = {}
    
    # Test lifespan to ensure routers are added
    async with app.router.lifespan_context(app):
        # Verify both routers are included
        routes = [route.path for route in app.routes]
        assert any(route.endswith("/health") for route in routes)
        assert any(route.endswith("/control") for route in routes)
        assert any(route.endswith("/extra") for route in routes)


@pytest.mark.asyncio
async def test_create_api_app_startup_error():
    """Test error handling during app startup."""
    router = APIRouter()
    
    class ErrorService(BaseService):
        def __init__(self):
            super().__init__("error_service")
        
        async def _start(self):
            raise ValueError("Start error")
    
    app = create_api_app(
        service_factory=ErrorService,
        prefix="/test",
        router=router
    )
    
    # Initialize app state
    app.state._state = {}
    
    # Test lifespan with startup error
    with pytest.raises(ValueError) as exc:
        async with app.router.lifespan_context(app):
            pass
    assert str(exc.value) == "Start error"
    assert app.state._state.get("service") is None


@pytest.mark.asyncio
async def test_create_api_app_shutdown_error():
    """Test error handling during app shutdown."""
    router = APIRouter()
    
    class ErrorService(BaseService):
        def __init__(self):
            super().__init__("error_service")
        
        async def _stop(self):
            raise ValueError("Stop error")
    
    app = create_api_app(
        service_factory=ErrorService,
        prefix="/test",
        router=router
    )
    
    # Initialize app state
    app.state._state = {}
    
    # Test lifespan with shutdown error
    async with app.router.lifespan_context(app):
        assert isinstance(app.state.service, ErrorService)
        assert app.state.service.is_running
    
    # Service should still be cleaned up despite error
    assert app.state._state.get("service") is None


def test_get_service_from_app():
    """Test getting service from app state."""
    app = FastAPI()
    service = BaseService("test_service")
    app.state.service = service
    
    # Test getting correct service type
    retrieved = get_service_from_app(app, BaseService)
    assert retrieved is service
    
    # Test getting wrong service type
    with pytest.raises(HTTPException) as exc:
        get_service_from_app(app, ConfigurableService)
    assert exc.value.status_code == 503
    assert "ConfigurableService not initialized" in exc.value.detail
    
    # Test when no service is set
    app.state.service = None
    with pytest.raises(HTTPException) as exc:
        get_service_from_app(app, BaseService)
    assert exc.value.status_code == 503
    assert "BaseService not initialized" in exc.value.detail
