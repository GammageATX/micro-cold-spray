"""Base utilities for configuration tests."""

from typing import Type, Optional
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_exceptions import ConfigError
from micro_cold_spray.api.config.config_app import ConfigApp


def create_test_app(service_class: Type[BaseService]) -> FastAPI:
    """Create a test application instance.
    
    Args:
        service_class: Service class to create app for
    
    Returns:
        FastAPI: Configured test application
    """
    app = ConfigApp()
    app.service_class = service_class
    return app


def create_test_client(app: FastAPI, service: Optional[BaseService] = None) -> TestClient:
    """Create a test client for the application.
    
    Args:
        app: FastAPI application instance
        service: Optional service instance to use
    
    Returns:
        TestClient: Configured test client
    """
    if service:
        app.dependency_overrides = {lambda: service}
    return TestClient(app)


async def test_service_lifecycle(service: BaseService):
    """Test standard service lifecycle.
    
    Args:
        service: Service instance to test
    """
    assert service.is_running
    await service.stop()
    assert not service.is_running


@pytest.fixture
def mock_service_error():
    """Create standardized service error mock.
    
    Returns:
        ConfigError: Standard error for service tests
    """
    return ConfigError("Service error")
