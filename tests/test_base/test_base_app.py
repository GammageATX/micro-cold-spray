"""Test base application module."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from micro_cold_spray.api.base.base_app import create_app
from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import (
    create_error,
    SERVICE_ERROR,
    NOT_IMPLEMENTED
)


class SimpleService(BaseService):
    """Simple service for testing."""
    
    async def _start(self) -> None:
        self._is_running = True
        
    async def _stop(self) -> None:
        self._is_running = False


def test_app_init():
    """Test app initialization."""
    app = create_app(
        service_class=SimpleService,
        title="Test API",
        service_name="test"
    )
    assert isinstance(app, FastAPI)
    assert app.title == "Test API"
    
    # Test service initialization
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_healthy"]
        assert len(data["services"]) == 1
        assert data["services"][0]["name"] == "test"
        assert data["services"][0]["is_healthy"]


def test_cors_middleware():
    """Test CORS middleware configuration."""
    app = create_app(
        service_class=SimpleService,
        title="Test API"
    )
    with TestClient(app) as client:
        # Test preflight request
        headers = {
            "Origin": "http://testserver",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        }
        response = client.options("/health", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["access-control-allow-origin"] == "*"
        assert "GET" in response.headers["access-control-allow-methods"]
        assert "Content-Type" in response.headers["access-control-allow-headers"]

        # Test actual request
        headers = {"Origin": "http://testserver"}
        response = client.get("/health", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["access-control-allow-origin"] == "*"


def test_health_endpoint():
    """Test health check endpoint."""
    app = create_app(
        service_class=SimpleService,
        title="Test API"
    )
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_healthy"]
        assert len(data["services"]) == 1
        assert data["services"][0]["is_healthy"]


def test_failing_service():
    """Test service that fails to start."""
    class FailingService(BaseService):
        async def _start(self) -> None:
            raise ValueError("Failed to start")
            
        async def _stop(self) -> None:
            raise ValueError("Failed to stop")

    app = create_app(
        service_class=FailingService,
        title="Test API"
    )
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert not data["is_healthy"]
        assert len(data["services"]) == 1
        assert not data["services"][0]["is_healthy"]
        assert "Failed to start" in data["services"][0]["error"]


def test_not_implemented_service():
    """Test service with unimplemented methods."""
    class NotImplementedService(BaseService):
        pass  # No _start/_stop implementation

    app = create_app(
        service_class=NotImplementedService,
        title="Test API"
    )
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert not data["is_healthy"]
        assert len(data["services"]) == 1
        assert not data["services"][0]["is_healthy"]
        assert "not implemented" in data["services"][0]["error"].lower()


def test_validation_error():
    """Test FastAPI validation error handling."""
    app = create_app(
        service_class=SimpleService,
        title="Test API"
    )
    
    @app.post("/test")
    async def test_endpoint(value: int):
        return {"value": value}

    with TestClient(app) as client:
        response = client.post("/test", json={"value": "not_an_int"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert data["detail"][0]["type"] == "int_parsing"


def test_exception_handling():
    """Test exception handling."""
    app = create_app(
        service_class=SimpleService,
        title="Test API"
    )
    
    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    with TestClient(app) as client:
        response = client.get("/error")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data
        assert "message" in data["detail"]
        assert "Test error" in data["detail"]["message"]
        assert "timestamp" in data["detail"]
        assert "context" in data["detail"]
