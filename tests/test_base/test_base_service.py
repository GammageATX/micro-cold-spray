"""Test base service module."""

import pytest
from fastapi import status

from tests.conftest import MockBaseService


class ErrorService(MockBaseService):
    """Service that raises errors during start/stop."""

    async def _start(self):
        """Start service with error."""
        raise RuntimeError("Start error")

    async def _stop(self):
        """Stop service with error."""
        raise RuntimeError("Stop error")


@pytest.fixture
def service():
    """Create test service."""
    return MockBaseService()


@pytest.fixture
def error_service():
    """Create service that raises errors."""
    return ErrorService()


class TestBaseService:
    """Test base service."""

    @pytest.mark.asyncio
    async def test_service_start(self, service):
        """Test service start."""
        await service.start()
        assert service.is_running

    @pytest.mark.asyncio
    async def test_service_stop(self, service):
        """Test service stop."""
        await service.start()
        await service.stop()
        assert not service.is_running

    @pytest.mark.asyncio
    async def test_service_health(self, service):
        """Test service health check."""
        await service.start()
        health = await service.health()
        assert health["is_healthy"] is True
        assert health["status"] == "running"
        assert health["context"]["service"] == service.name

    @pytest.mark.asyncio
    async def test_service_health_not_running(self, service):
        """Test health check when service is not running."""
        health = await service.health()
        assert health["is_healthy"] is False
        assert health["status"] == "stopped"
        assert health["context"]["service"] == service.name

    @pytest.mark.asyncio
    async def test_start_already_running(self, service):
        """Test starting already running service."""
        await service.start()
        with pytest.raises(ValueError) as exc:
            await service.start()
        assert "already running" in str(exc.value)

    @pytest.mark.asyncio
    async def test_stop_not_running(self, service):
        """Test stopping not running service."""
        with pytest.raises(ValueError) as exc:
            await service.stop()
        assert "not running" in str(exc.value)

    @pytest.mark.asyncio
    async def test_start_error(self, error_service):
        """Test error during service start."""
        with pytest.raises(RuntimeError) as exc:
            await error_service.start()
        assert "Start error" in str(exc.value)
        assert not error_service.is_running

    @pytest.mark.asyncio
    async def test_stop_error(self, error_service):
        """Test error during service stop."""
        error_service._is_running = True  # Force running state
        with pytest.raises(RuntimeError) as exc:
            await error_service.stop()
        assert "Stop error" in str(exc.value)
        assert error_service.is_running  # Service should still be running after failed stop

    def test_service_name(self):
        """Test service name."""
        service = MockBaseService("custom_name")
        assert service.name == "custom_name"

        service = MockBaseService()
        assert service.name == "test_service"
