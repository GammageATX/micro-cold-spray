"""Tests for base service."""

import pytest
from fastapi import status

from micro_cold_spray.api.base.base_service import BaseService


class TestBaseService:
    """Test base service."""

    @pytest.mark.asyncio
    async def test_service_start(self):
        """Test service start."""
        service = BaseService()
        await service.start()
        assert service.is_running is True

    @pytest.mark.asyncio
    async def test_service_stop(self):
        """Test service stop."""
        service = BaseService()
        await service.start()
        await service.stop()
        assert service.is_running is False

    @pytest.mark.asyncio
    async def test_service_start_already_running(self):
        """Test starting already running service."""
        service = BaseService()
        await service.start()
        with pytest.raises(Exception) as exc:
            await service.start()
        assert exc.value.status_code == status.HTTP_409_CONFLICT
        assert "already running" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == "baseservice"

    @pytest.mark.asyncio
    async def test_service_stop_not_running(self):
        """Test stopping not running service."""
        service = BaseService()
        with pytest.raises(Exception) as exc:
            await service.stop()
        assert exc.value.status_code == status.HTTP_409_CONFLICT
        assert "not running" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == "baseservice"

    @pytest.mark.asyncio
    async def test_service_start_error(self):
        """Test service start error."""
        class ErrorService(BaseService):
            async def _start(self):
                raise ValueError("Start error")

        service = ErrorService()
        with pytest.raises(Exception) as exc:
            await service.start()
        assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "failed to start" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == "errorservice"
        assert isinstance(exc.value.__cause__, ValueError)

    @pytest.mark.asyncio
    async def test_service_stop_error(self):
        """Test service stop error."""
        class ErrorService(BaseService):
            async def _start(self):
                self._is_running = True

            async def _stop(self):
                raise ValueError("Stop error")

        service = ErrorService()
        await service.start()
        with pytest.raises(Exception) as exc:
            await service.stop()
        assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "failed to stop" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == "errorservice"
        assert isinstance(exc.value.__cause__, ValueError)

    @pytest.mark.asyncio
    async def test_service_not_implemented(self):
        """Test service with unimplemented methods."""
        service = BaseService()
        with pytest.raises(Exception) as exc:
            await service._start()
        assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "not implemented" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == "baseservice"

    @pytest.mark.asyncio
    async def test_service_health(self):
        """Test service health check."""
        service = BaseService()
        health = await service.health()
        assert health["is_healthy"] is False
        assert health["status"] == "not running"
        assert health["context"]["service"] == "baseservice"

        await service.start()
        health = await service.health()
        assert health["is_healthy"] is True
        assert health["status"] == "running"
        assert health["context"]["service"] == "baseservice"

    def test_service_name(self):
        """Test service name."""
        service = BaseService()
        assert service.name == "baseservice"

        service = BaseService("custom")
        assert service.name == "custom"
