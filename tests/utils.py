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
    error_code: str,
    message: str = None
) -> None:
    """Assert that an error response matches expected format.
    
    Args:
        response: FastAPI response
        status_code: Expected HTTP status code
        error_code: Expected error code
        message: Expected error message (optional)
    """
    assert response.status_code == status_code
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == error_code
    if message:
        assert message.lower() in data["error"]["message"].lower()


def assert_health_response(response: Any, service_name: str) -> None:
    """Assert that a health check response is valid.
    
    Args:
        response: FastAPI response
        service_name: Expected service name
    """
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "error"]
    assert data["service_name"] == service_name
    assert "version" in data
    assert "is_running" in data
    assert "timestamp" in data
    assert "uptime" in data
