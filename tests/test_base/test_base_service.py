"""Tests for base service."""

import pytest
from fastapi import status

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import create_error
from tests.test_base.conftest import (
    MockBaseService,
    FailingService,
    ErrorService
)


class TestBaseService:
    """Test base service."""

    @pytest.mark.asyncio
    async def test_service_start(self):
        """Test service start."""
        service = MockBaseService()
        assert not service.is_running
        await service.start()
        assert service.is_running

    @pytest.mark.asyncio
    async def test_service_stop(self):
        """Test service stop."""
        service = MockBaseService()
        await service.start()
        assert service.is_running
        await service.stop()
        assert not service.is_running

    @pytest.mark.asyncio
    async def test_service_start_already_running(self):
        """Test starting already running service."""
        service = MockBaseService()
        await service.start()
        with pytest.raises(Exception) as exc:
            await service.start()
        assert exc.value.status_code == status.HTTP_409_CONFLICT
        assert "already running" in str(exc.value.detail["message"])

    @pytest.mark.asyncio
    async def test_service_stop_not_running(self):
        """Test stopping not running service."""
        service = MockBaseService()
        with pytest.raises(Exception) as exc:
            await service.stop()
        assert exc.value.status_code == status.HTTP_409_CONFLICT
        assert "not running" in str(exc.value.detail["message"])

    @pytest.mark.asyncio
    async def test_service_start_error(self):
        """Test service start error."""
        service = FailingService()
        with pytest.raises(Exception) as exc:
            await service.start()
        assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Failed to start" in str(exc.value.detail["message"])

    @pytest.mark.asyncio
    async def test_service_stop_error(self):
        """Test service stop error."""
        service = ErrorService()
        await service.start()
        with pytest.raises(Exception) as exc:
            await service.stop()
        assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Failed to stop" in str(exc.value.detail["message"])

    @pytest.mark.asyncio
    async def test_service_not_implemented(self):
        """Test service with unimplemented methods."""
        service = BaseService()
        with pytest.raises(Exception) as exc:
            await service.start()
        assert exc.value.status_code == status.HTTP_501_NOT_IMPLEMENTED
        assert "does not implement start" in str(exc.value.detail["message"])

        service._is_running = True  # Force running state
        with pytest.raises(Exception) as exc:
            await service.stop()
        assert exc.value.status_code == status.HTTP_501_NOT_IMPLEMENTED
        assert "does not implement stop" in str(exc.value.detail["message"])

    @pytest.mark.asyncio
    async def test_service_health(self):
        """Test service health check."""
        service = MockBaseService()
        health = await service.health()
        assert not health["is_healthy"]
        assert health["status"] == "stopped"
        assert health["context"]["service"] == service.name

        await service.start()
        health = await service.health()
        assert health["is_healthy"]
        assert health["status"] == "running"
        assert health["context"]["service"] == service.name

    def test_service_name(self):
        """Test service name."""
        service = MockBaseService()
        assert service.name == "mockbaseservice"

        service = MockBaseService(name="test")
        assert service.name == "test"
