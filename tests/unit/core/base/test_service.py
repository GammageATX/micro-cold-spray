"""Unit tests for base service functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from micro_cold_spray.core.base.services.base_service import BaseService
from micro_cold_spray.core.errors.exceptions import ServiceError

class TestBaseService:
    """Test cases for BaseService class."""

    @pytest.fixture
    def service(self):
        """Create a test service instance."""
        return BaseService("test_service")

    @pytest.mark.asyncio
    async def test_service_lifecycle(self, service):
        """Test service start/stop lifecycle."""
        assert not service.is_running
        assert service.start_time is None

        # Test start
        await service.start()
        assert service.is_running
        assert service.start_time is not None
        assert service.uptime > 0

        # Test stop
        await service.stop()
        assert not service.is_running
        assert service.start_time is None
        assert service.uptime is None

    @pytest.mark.asyncio
    async def test_service_restart(self, service):
        """Test service restart."""
        await service.start()
        first_start_time = service.start_time

        await service.restart()
        assert service.is_running
        assert service.start_time > first_start_time

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test health check functionality."""
        # Test uninitialized state
        health = await service.check_health()
        assert health["status"] == "error"
        assert "Service not initialized" in health["error"]
        assert not health["service_info"]["running"]
        
        # Test running state
        await service.start()
        health = await service.check_health()
        assert health["status"] == "ok"
        assert health["service_info"]["running"]
        assert health["service_info"]["name"] == "test_service"
        assert health["service_info"]["version"] == "1.0.0"
        assert health["service_info"]["uptime"] is not None
        
        # Test error state
        service._error = "Test error"
        health = await service.check_health()
        assert health["status"] == "error"
        assert health["error"] == "Test error"
        
        # Test degraded state
        service._error = None
        service._message = "Performance degraded"
        health = await service.check_health()
        assert health["status"] == "degraded"
        assert health["message"] == "Performance degraded"
        
        # Test stopped state
        await service.stop()
        health = await service.check_health()
        assert health["status"] == "stopped"
        assert not health["service_info"]["running"]

    @pytest.mark.asyncio
    async def test_service_properties(self, service):
        """Test service property getters."""
        assert service.service_name == "test_service"
        assert service.version == "1.0.0"
        assert not service.is_running
        assert service.uptime is None

        await service.start()
        assert service.is_running
        assert isinstance(service.uptime, timedelta)
        assert service.uptime.total_seconds() >= 0

    @pytest.mark.asyncio
    async def test_error_handling(self, service):
        """Test service error handling."""
        # Test start error
        service._start = AsyncMock(side_effect=Exception("Start failed"))
        with pytest.raises(ServiceError, match="Start failed"):
            await service.start()
        assert not service.is_running
        assert service._error == "Start failed"

        # Test stop error
        service._stop = AsyncMock(side_effect=Exception("Stop failed"))
        with pytest.raises(ServiceError, match="Stop failed"):
            await service.stop()

    @pytest.mark.asyncio
    async def test_health_check_error(self):
        """Test health check with error."""
        class ErrorService(BaseService):
            async def _check_health(self):
                raise ValueError("Health check error")
                
        service = ErrorService("error_service")
        await service.start()
        
        health = await service.check_health()
        assert health["status"] == "error"
        assert "Health check error" in health["error"]
        assert health["service_info"]["error"] == "Health check error" 