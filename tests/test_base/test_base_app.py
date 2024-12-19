"""Test base app module."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from contextlib import asynccontextmanager
from datetime import datetime

from micro_cold_spray.api.base.base_app import BaseApp
from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import ServiceError, AppErrorCode
from micro_cold_spray.api.base.base_registry import register_service, clear_services


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

    async def _start(self) -> None:
        """Start mock service."""
        self._mock_metrics["start_count"] += 1
        self._is_running = True
        self._is_initialized = True
        self._start_time = datetime.now()

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
        return {"status": "healthy"}

    @property
    def metrics(self) -> dict:
        """Get service metrics."""
        return self._mock_metrics.copy()


class TestBaseApp:
    """Test base application."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        clear_services()
        yield
        clear_services()

    @pytest.fixture
    def base_app(self):
        """Create base app with mock service."""
        app = BaseApp(
            service_class=MockService,
            title="Test API",
            service_name="test_service",
            enable_cors=True,
            enable_metrics=True,
        )
        return app

    def test_lifespan(self, base_app):
        """Test app lifespan."""
        with TestClient(base_app) as client:
            # First request may fail as service is starting
            for _ in range(3):  # Retry a few times
                response = client.get("/health")
                if response.status_code == 200:
                    break
            assert response.status_code == 200

    def test_lifespan_with_dependencies(self, base_app):
        """Test app lifespan with dependencies."""
        mock_dependency = AsyncMock()

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await mock_dependency()
            service = MockService("test_service")
            register_service(service)
            await service.start()
            try:
                yield
            finally:
                await service.stop()
                clear_services()

        # Override the lifespan
        base_app.router.lifespan_context = lifespan

        with TestClient(base_app) as client:
            # First request may fail as service is starting
            for _ in range(3):  # Retry a few times
                response = client.get("/health")
                if response.status_code == 200:
                    break
            assert response.status_code == 200
            mock_dependency.assert_called_once()

    def test_health_endpoint_success(self, base_app):
        """Test health endpoint success."""
        with TestClient(base_app) as client:
            # First request may fail as service is starting
            for _ in range(3):  # Retry a few times
                response = client.get("/health")
                if response.status_code == 200:
                    break
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}

    def test_health_endpoint_service_error(self, base_app):
        """Test health endpoint with service error."""
        # Override lifespan to register but not start service
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            service = MockService("test_service")
            register_service(service)
            yield

        base_app.router.lifespan_context = lifespan

        with TestClient(base_app) as client:
            response = client.get("/health")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert response.json()["code"] == AppErrorCode.SERVICE_NOT_RUNNING

    def test_health_endpoint_not_running(self, base_app):
        """Test health endpoint when service is not running."""
        # Override lifespan to register but not start service
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            service = MockService("test_service")
            register_service(service)
            yield

        base_app.router.lifespan_context = lifespan

        with TestClient(base_app) as client:
            response = client.get("/health")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert response.json()["code"] == AppErrorCode.SERVICE_NOT_RUNNING

    def test_metrics_endpoint_enabled(self, base_app):
        """Test metrics endpoint enabled."""
        with TestClient(base_app) as client:
            response = client.get("/metrics")
            assert response.status_code == 200
            assert "start_count" in response.json()

    def test_logging_middleware(self, base_app):
        """Test logging middleware."""
        with TestClient(base_app) as client:
            response = client.get("/health")
            assert response.status_code == 200

    def test_error_handler_unexpected(self, base_app):
        """Test unexpected error handler."""
        # Override lifespan to register service that raises error
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            service = MockService("test_service")
            register_service(service)
            service.check_health = AsyncMock(side_effect=RuntimeError("Unexpected error"))
            yield

        base_app.router.lifespan_context = lifespan

        with TestClient(base_app) as client:
            response = client.get("/health")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert response.json()["code"] == AppErrorCode.INTERNAL_ERROR

    def test_get_service(self, base_app):
        """Test get service."""
        with TestClient(base_app) as client:
            response = client.get("/health")
            assert response.status_code == 200
