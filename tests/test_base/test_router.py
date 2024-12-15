"""Tests for base router."""

import pytest
from fastapi import FastAPI, APIRouter, HTTPException
from micro_cold_spray.api.base.router import add_health_endpoints
from micro_cold_spray.api.base.service import BaseService


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


@pytest.mark.asyncio
async def test_control_endpoint(test_router):
    """Test service control endpoint."""
    router, service = test_router
    
    # Get control route handler
    control_route = next(r for r in router.routes if r.path == "/control")
    
    # Test start
    response = await control_route.endpoint(action="start")
    assert response["status"] == "started"
    assert service.is_running
    
    # Test stop
    response = await control_route.endpoint(action="stop")
    assert response["status"] == "stopped"
    assert not service.is_running
    
    # Test invalid action
    try:
        await control_route.endpoint(action="invalid")
        pytest.fail("Should have raised HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Invalid action" in str(exc.detail)


@pytest.mark.asyncio
async def test_health_check_error(test_router):
    """Test health check error handling."""
    router, service = test_router
    
    # Force error in health check
    async def check_health():
        raise ValueError("Test error")
    service.check_health = check_health
    
    health_route = next(r for r in router.routes if r.path == "/health")
    with pytest.raises(HTTPException) as exc:
        await health_route.endpoint()
    assert exc.value.status_code == 500
    assert "Test error" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_service_error(test_router):
    """Test service operation error handling."""
    router, service = test_router
    
    # Force error in service start
    async def _start():
        raise ValueError("Start error")
    service._start = _start
    
    control_route = next(r for r in router.routes if r.path == "/control")
    with pytest.raises(HTTPException) as exc:
        await control_route.endpoint(action="start")
    assert exc.value.status_code == 500
    assert "Start error" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_health_check_stopped(test_router):
    """Test health check when service is stopped."""
    router, service = test_router
    
    # Stop service
    await service.stop()
    
    # Get route handler
    health_route = next(r for r in router.routes if r.path == "/health")
    response = await health_route.endpoint()
    
    assert response["status"] == "stopped"
    assert response["service_info"]["running"] is False


@pytest.mark.asyncio
async def test_health_check_error_status(test_router):
    """Test health check with error status."""
    router, service = test_router
    
    # Start service
    await service.start()
    
    # Mock health check to return error status
    async def check_health():
        return {"status": "error", "error": "Test error"}
    service.check_health = check_health
    
    # Get route handler
    health_route = next(r for r in router.routes if r.path == "/health")
    response = await health_route.endpoint()
    
    assert response["status"] == "error"
    assert response["service_info"]["error"] == "Test error"


@pytest.mark.asyncio
async def test_health_check_degraded(test_router):
    """Test health check with degraded status."""
    router, service = test_router
    
    # Start service
    await service.start()
    
    # Mock health check to return degraded status
    async def check_health():
        return {"status": "degraded", "message": "Performance degraded"}
    service.check_health = check_health
    
    # Get route handler
    health_route = next(r for r in router.routes if r.path == "/health")
    response = await health_route.endpoint()
    
    assert response["status"] == "degraded"
    assert "Performance degraded" in response["service_info"]["message"]


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
    assert "Start error" in str(exc.value.detail)
