"""Test base service functionality."""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, AsyncGenerator

from micro_cold_spray.api.base import BaseService
from micro_cold_spray.api.base.base_errors import ServiceError


class MockService(BaseService):
    """Mock service for testing."""

    def __init__(self, service_name: str, dependencies: Optional[List[str]] = None):
        """Initialize mock service."""
        super().__init__(service_name, dependencies)
        self._mock_start_called = False
        self._mock_stop_called = False

    async def _start(self) -> None:
        """Start implementation."""
        self._mock_start_called = True

    async def _stop(self) -> None:
        """Stop implementation."""
        self._mock_stop_called = True


class TestBaseService:
    """Test base service functionality."""

    @pytest.fixture
    async def service(self) -> AsyncGenerator[MockService, None]:
        """Create a mock service."""
        service = MockService("test_service")
        yield service
        if service.is_running:
            await service.stop()

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test service initialization."""
        service = MockService("test_service")
        assert service._service_name == "test_service"
        assert not service.is_running
        assert not service.is_initialized
        assert service.metrics == {
            "start_count": 0,
            "stop_count": 0,
            "error_count": 0,
            "last_error": None
        }

    @pytest.mark.asyncio
    async def test_start_stop(self, service):
        """Test service start and stop."""
        await service.start()
        assert service.is_running
        assert service.is_initialized
        assert service._mock_start_called
        assert service.metrics["start_count"] == 1

        await service.stop()
        assert not service.is_running
        assert service._mock_stop_called
        assert service.metrics["stop_count"] == 1

    @pytest.mark.asyncio
    async def test_start_error(self):
        """Test start error."""
        service = BaseService("test_service")
        with pytest.raises(ServiceError) as exc:
            await service.start()
        assert "Failed to start service" in str(exc.value)
        assert service.metrics["error_count"] == 1
        assert "Subclasses must implement _start" in service.metrics["last_error"]

    @pytest.mark.asyncio
    async def test_stop_error(self):
        """Test stop error."""
        service = BaseService("test_service")
        service._is_running = True
        with pytest.raises(ServiceError) as exc:
            await service.stop()
        assert "Failed to stop service" in str(exc.value)
        assert service.metrics["error_count"] == 1
        assert "Subclasses must implement _stop" in service.metrics["last_error"]

    @pytest.mark.asyncio
    async def test_check_health_success(self, service):
        """Test successful health check."""
        await service.start()
        health = await service.check_health()
        assert health["status"] == "ok"
        assert health["service_info"]["name"] == "test_service"
        assert health["service_info"]["running"] is True
        assert isinstance(health["service_info"]["uptime"], str)

    @pytest.mark.asyncio
    async def test_check_health_not_running(self, service):
        """Test health check when not running."""
        with pytest.raises(ServiceError) as exc:
            await service.check_health()
        assert "Health check failed" in str(exc.value)
        assert service.metrics["error_count"] == 1
        assert "Service is not running" in service.metrics["last_error"]

    @pytest.mark.asyncio
    async def test_uptime(self, service):
        """Test service uptime calculation."""
        await service.start()
        assert isinstance(service.uptime, timedelta)
        assert service.uptime.total_seconds() >= 0

    @pytest.mark.asyncio
    async def test_metrics(self, service):
        """Test service metrics."""
        await service.start()
        assert service.metrics["start_count"] == 1
        assert service.metrics["stop_count"] == 0
        assert service.metrics["error_count"] == 0
        assert service.metrics["last_error"] is None

        await service.stop()
        assert service.metrics["start_count"] == 1
        assert service.metrics["stop_count"] == 1
        assert service.metrics["error_count"] == 0
        assert service.metrics["last_error"] is None
