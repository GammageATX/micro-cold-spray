"""Tests for base service functionality."""

import pytest
import asyncio
from datetime import timedelta
from micro_cold_spray.api.base import BaseService


class TestBaseService:
    """Test base service functionality."""
    
    def test_init(self):
        """Test service initialization."""
        service = BaseService("test_service")
        assert service._service_name == "test_service"
        assert not service._is_initialized
        assert not service._is_running
        assert service._start_time is None
        assert service._error is None
        assert service._message is None
        assert service.version == "1.0.0"
        
    def test_properties(self):
        """Test service properties."""
        service = BaseService("test_service")
        assert not service.is_running
        assert not service.is_initialized
        assert service.uptime is None

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test service start/stop lifecycle."""
        service = BaseService("test_service")
        
        # Test start
        await service.start()
        assert service.is_running
        assert service.is_initialized
        assert service.uptime is not None
        assert isinstance(service.uptime, timedelta)
        
        # Test duplicate start
        await service.start()  # Should just log warning
        
        # Test stop
        await service.stop()
        assert not service.is_running
        assert service.uptime is None
        
        # Test duplicate stop
        await service.stop()  # Should just log warning

    @pytest.mark.asyncio
    async def test_restart(self):
        """Test service restart."""
        service = BaseService("test_service")
        
        # Start and verify
        await service.start()
        assert service.is_running
        first_start_time = service._start_time
        
        # Wait a bit to ensure different start time
        await asyncio.sleep(0.1)
        
        # Restart and verify
        await service.restart()
        assert service.is_running
        assert service._start_time > first_start_time

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling during start/stop."""
        class ErrorService(BaseService):
            async def _start(self):
                raise ValueError("Start error")
                
            async def _stop(self):
                raise ValueError("Stop error")
                
        service = ErrorService("error_service")
        
        # Test start error
        with pytest.raises(ValueError, match="Start error"):
            await service.start()
        assert not service.is_running
        assert service._error == "Start error"
            
        # Force service into running state to test stop error
        service._is_running = True
        
        # Test stop error
        with pytest.raises(ValueError, match="Stop error"):
            await service.stop()
        assert service._error == "Stop error"

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality."""
        service = BaseService("test_service")
        
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
