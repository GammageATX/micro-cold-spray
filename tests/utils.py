"""Shared test utilities and helper functions."""

import asyncio
from typing import Any, TypeVar, Awaitable
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient

T = TypeVar('T')


def async_return(result: T) -> Awaitable[T]:
    """Create an awaitable that returns the given result."""
    f = asyncio.Future()
    f.set_result(result)
    return f


def create_test_app(
    routes: list = None,
    dependencies: list = None,
    middleware: list = None
) -> FastAPI:
    """Create a test FastAPI app with optional routes and middleware.
    
    Args:
        routes: List of APIRouter instances to include
        dependencies: List of FastAPI dependencies
        middleware: List of middleware classes to add
        
    Returns:
        Configured FastAPI instance
    """
    app = FastAPI()
    
    # Add routes
    if routes:
        for router in routes:
            app.include_router(router)
            
    # Add dependencies
    if dependencies:
        for depends in dependencies:
            app.dependency_overrides[depends] = lambda: None
            
    # Add middleware
    if middleware:
        for mw in middleware:
            app.add_middleware(mw)
            
    return app


def create_test_client(app: FastAPI) -> TestClient:
    """Create a TestClient with common configuration.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Configured TestClient
    """
    client = TestClient(app)
    client.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    return client


class AsyncMockWithSetup:
    """Mock class that supports async setup/teardown."""
    
    def __init__(self):
        """Initialize mock."""
        self.setup_called = False
        self.teardown_called = False
        
    async def setup(self):
        """Setup mock."""
        self.setup_called = True
        
    async def teardown(self):
        """Teardown mock."""
        self.teardown_called = True


def mock_service_factory(
    service_name: str = "test_service",
    version: str = "1.0.0",
    is_running: bool = True,
    start_time: datetime = None
) -> Any:
    """Create a mock service with standard attributes.
    
    Args:
        service_name: Name of the service
        version: Service version
        is_running: Whether service is running
        start_time: Service start time (defaults to now)
        
    Returns:
        Mock service instance
    """
    from unittest.mock import AsyncMock, PropertyMock
    
    service = AsyncMock()
    type(service)._service_name = PropertyMock(return_value=service_name)
    type(service).version = PropertyMock(return_value=version)
    type(service).is_running = PropertyMock(return_value=is_running)
    
    if start_time is None:
        start_time = datetime.now()
    type(service).start_time = PropertyMock(return_value=start_time)
    type(service).uptime = PropertyMock(
        return_value=str(datetime.now() - start_time)
    )
    
    async def mock_health():
        return {
            "is_healthy": is_running,
            "status": "running" if is_running else "stopped",
            "context": {
                "service": service_name,
                "version": version,
                "uptime": str(datetime.now() - start_time),
                "metrics": {
                    "start_count": 1 if is_running else 0,
                    "stop_count": 0 if is_running else 1,
                    "error_count": 0,
                    "last_error": None
                }
            }
        }
    service.health = AsyncMock(side_effect=mock_health)
    
    return service


def assert_json_structure(data: dict, expected_keys: list) -> None:
    """Assert that a JSON response has the expected structure.
    
    Args:
        data: JSON response data
        expected_keys: List of expected top-level keys
    """
    assert isinstance(data, dict), "Response must be a dictionary"
    assert set(data.keys()) == set(expected_keys), \
        f"Expected keys {expected_keys}, got {list(data.keys())}"


def assert_error_response(
    response: Any,
    status_code: int,
    message: str = None,
    context: dict = None
) -> None:
    """Assert that an error response matches expected format.
    
    Args:
        response: FastAPI response
        status_code: Expected HTTP status code
        message: Expected error message (optional)
        context: Expected error context (optional)
    """
    assert response.status_code == status_code
    data = response.json()
    assert "detail" in data
    assert "message" in data["detail"]
    if message:
        assert message.lower() in data["detail"]["message"].lower()
    if context:
        assert "context" in data["detail"]
        for key, value in context.items():
            assert data["detail"]["context"][key] == value


def assert_health_response(response: Any, service_name: str) -> None:
    """Assert that a health check response is valid.
    
    Args:
        response: FastAPI response
        service_name: Expected service name
    """
    assert response.status_code == 200
    data = response.json()
    assert "is_healthy" in data
    assert "status" in data
    assert data["status"] in ["running", "stopped", "error", "degraded"]
    assert "context" in data
    assert data["context"]["service"] == service_name
    assert "version" in data["context"]
    assert "uptime" in data["context"]
    assert "metrics" in data["context"]
