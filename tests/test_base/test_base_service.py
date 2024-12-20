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
async def error_service():
    """Create service that raises errors."""
    return ErrorService()


class TestBaseService:
    """Test base service."""

    @pytest.mark.asyncio
    async def test_service_start(self, base_service):
        """Test service start."""
        await base_service.start()
        assert base_service.is_running

    @pytest.mark.asyncio
    async def test_service_stop(self, base_service):
        """Test service stop."""
        await base_service.start()
        await base_service.stop()
        assert not base_service.is_running

    @pytest.mark.asyncio
    async def test_service_health(self, base_service):
        """Test service health check."""
        await base_service.start()
        health = await base_service.health()
        assert health["is_healthy"] is True
        assert health["status"] == "running"
        assert health["context"]["service"] == base_service.name

    @pytest.mark.asyncio
    async def test_service_health_not_running(self, base_service):
        """Test health check when service is not running."""
        health = await base_service.health()
        assert health["is_healthy"] is False
        assert health["status"] == "stopped"
        assert health["context"]["service"] == base_service.name

    @pytest.mark.asyncio
    async def test_start_already_running(self, base_service):
        """Test starting already running service."""
        await base_service.start()
        with pytest.raises(Exception) as exc:
            await base_service.start()
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already running" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_stop_not_running(self, base_service):
        """Test stopping not running service."""
        with pytest.raises(Exception) as exc:
            await base_service.stop()
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "not running" in str(exc.value.detail)

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

    @pytest.mark.asyncio
    async def test_service_name(self):
        """Test service name."""
        service = MockBaseService("custom_name")
        assert service.name == "custom_name"

        service = MockBaseService()
        assert service.name == "test_service"
