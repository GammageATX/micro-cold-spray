"""Test base router module."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from micro_cold_spray.api.base.base_errors import ServiceError, AppErrorCode
from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_router import BaseRouter, HealthResponse


class MockService(BaseService):
    """Mock service for testing."""

    def __init__(self, name: str) -> None:
        """Initialize mock service."""
        super().__init__(name)
        self._mock_metrics = {
            "start_count": 0,
            "stop_count": 0,
            "error_count": 0,
            "last_error": None,
        }
        self._start_time = datetime.now()

    async def _start(self) -> None:
        """Start mock service."""
        self._mock_metrics["start_count"] += 1
        self._is_running = True
        self._is_initialized = True

    async def _stop(self) -> None:
        """Stop mock service."""
        self._mock_metrics["stop_count"] += 1
        self._is_running = False

    async def check_health(self) -> dict:
        """Check service health."""
        if not self._is_running:
            raise ServiceError(
                "Service not running",
                error_code=AppErrorCode.SERVICE_NOT_RUNNING,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return {
            "status": "ok",
            "service_info": {
                "name": self.service_name,
                "running": self.is_running,
                "uptime": str(datetime.now() - self._start_time),
                "metrics": self.metrics
            }
        }


class TestBaseRouter:
    """Test base router functionality."""

    @pytest.fixture
    def app(self):
        """Create test app with router."""
        app = FastAPI()
        router = BaseRouter(service_class=MockService)
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_service(self):
        """Create and register mock service."""
        from micro_cold_spray.api.base.base_registry import register_service, clear_services
        clear_services()
        service = MockService("test_service")
        register_service(service)
        yield service
        clear_services()

    def test_router_initialization(self):
        """Test router initialization."""
        router = BaseRouter(service_class=MockService)
        assert router.service_class == MockService
        routes = [route for route in router.routes if route.path == "/health"]
        assert len(routes) == 1
        assert routes[0].methods == {"GET"}
        assert routes[0].response_model == HealthResponse

    def test_health_check_success(self, client, mock_service):
        """Test successful health check."""
        # Start the service
        import asyncio
        asyncio.run(mock_service.start())

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service_info"]["name"] == "test_service"
        assert data["service_info"]["running"] is True
        assert "uptime" in data["service_info"]
        assert "metrics" in data["service_info"]

    def test_health_check_service_error(self, client, mock_service):
        """Test health check with service error."""
        # Don't start the service to trigger error
        response = client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["detail"]["detail"] == "Service not running"
        assert data["detail"]["code"] == AppErrorCode.SERVICE_NOT_RUNNING

    def test_health_check_unexpected_error(self, client, mock_service):
        """Test health check with unexpected error."""
        # Mock check_health to raise unexpected error
        mock_service.check_health = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        response = client.get("/health")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Unexpected error during health check" in data["detail"]["detail"]
        assert data["detail"]["code"] == AppErrorCode.INTERNAL_ERROR

    def test_health_response_validation(self, client, mock_service):
        """Test health response validation."""
        # Start the service
        import asyncio
        asyncio.run(mock_service.start())

        # Mock check_health to return invalid response
        async def invalid_health():
            return {"invalid": "response"}
        mock_service.check_health = invalid_health

        response = client.get("/health")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Invalid health response format" in data["detail"]["detail"]
        assert data["detail"]["code"] == AppErrorCode.INTERNAL_ERROR

    def test_health_check_service_not_found(self, client):
        """Test health check when service is not registered."""
        from micro_cold_spray.api.base.base_registry import clear_services
        clear_services()

        response = client.get("/health")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Service MockService not initialized" in data["detail"]["detail"]
        assert data["detail"]["code"] == AppErrorCode.INTERNAL_ERROR
