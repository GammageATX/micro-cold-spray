"""Tests for base router."""

import pytest
from fastapi import FastAPI, APIRouter, HTTPException
from micro_cold_spray.api.base.router import add_health_endpoints
from micro_cold_spray.api.base.service import BaseService


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
    assert error_detail["error"] == "Internal Server Error"
    assert error_detail["message"] == "Start error"
