"""Tests for base service functionality."""

import pytest
import asyncio
from datetime import timedelta
from micro_cold_spray.api.base import BaseService


class ErrorInHealthCheckService(BaseService):
    """Service that raises error in health check."""
    
    def __init__(self):
        """Initialize service."""
        super().__init__("error_health_service")
        
    async def _check_health(self) -> None:
        """Raise error during health check."""
        raise ValueError("Health check error")


class ErrorInStopService(BaseService):
    """Service that raises error in stop."""
    
    def __init__(self):
        """Initialize service."""
        super().__init__("error_stop_service")
        
    async def _stop(self) -> None:
        """Raise error during stop."""
        raise ValueError("Stop error")


class CustomHealthCheckService(BaseService):
    """Service with custom health check implementation."""
    
    def __init__(self):
        """Initialize service."""
        super().__init__("custom_health_service")
        self._custom_health = {}
        
    async def check_health(self) -> dict:
        """Check service health status."""
        try:
            # Get base service info
            health_info = {
                "service_info": {
                    "name": self._service_name,
                    "version": self.version,
                    "running": self._is_running,
                    "uptime": str(self.uptime) if self.uptime else None
                }
            }
            
            # Return custom data if set
            if self._custom_health:
                # Handle error data
                if "error" in self._custom_health:
                    health_info.update({
                        "status": "error",
                        "error": self._custom_health["error"]
                    })
                # Handle warning data
                elif "status" in self._custom_health and self._custom_health["status"] == "warning":
                    health_info.update(self._custom_health)
                # Handle invalid data
                else:
                    health_info.update({
                        "status": "error",
                        "error": "Invalid health check data"
                    })
                return health_info
            
            # Otherwise, use base health check logic
            health_info.update(await self._check_health())
            
            # Set status based on service state
            if not self._is_initialized:
                health_info["status"] = "error"
                health_info["error"] = "Service not initialized"
                health_info["service_info"]["error"] = "Service not initialized"
            elif not self._is_running:
                health_info["status"] = "stopped"
                if self._error:
                    health_info["error"] = self._error
                    health_info["service_info"]["error"] = self._error
            elif self._error:
                health_info["status"] = "error"
                health_info["error"] = self._error
                health_info["service_info"]["error"] = self._error
            elif self._message:
                health_info["status"] = "degraded"
                health_info["message"] = self._message
                health_info["service_info"]["message"] = self._message
            else:
                health_info["status"] = "ok"
            
            return health_info
        except Exception as e:
            self._error = str(e)
            return {
                "status": "error",
                "error": str(e),
                "service_info": {
                    "name": self._service_name,
                    "version": self.version,
                    "running": self._is_running,
                    "uptime": str(self.uptime) if self.uptime else None,
                    "error": str(e)
                }
            }
        
    async def _check_health(self) -> dict:
        """Return custom health check data."""
        # Get base health data
        await super()._check_health()  # Just to validate initialization
        return {}
        
    def set_health_data(self, data: dict) -> None:
        """Set custom health check data."""
        self._custom_health = data


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

    def test_init_with_custom_version(self):
        """Test service initialization with custom version."""
        service = BaseService("test_service", version="2.0.0")
        assert service.version == "2.0.0"
        
    def test_properties(self):
        """Test service properties."""
        service = BaseService("test_service")
        assert not service.is_running
        assert not service.is_initialized
        assert service.uptime is None
        assert service.service_name == "test_service"
        assert service.error is None
        assert service.message is None

    def test_version_property(self):
        """Test version property getter and setter."""
        service = BaseService("test_service")
        assert service.version == "1.0.0"
        service.version = "2.0.0"
        assert service.version == "2.0.0"

    def test_error_message_properties(self):
        """Test error and message property setters."""
        service = BaseService("test_service")
        service._error = "Test error"
        service._message = "Test message"
        assert service.error == "Test error"
        assert service.message == "Test message"

    @pytest.mark.asyncio
    async def test_uptime_accuracy(self):
        """Test uptime calculation accuracy."""
        service = BaseService("test_service")
        await service.start()
        await asyncio.sleep(0.1)  # Wait a bit
        uptime = service.uptime
        assert isinstance(uptime, timedelta)
        assert uptime.total_seconds() >= 0.1
        await service.stop()

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

    @pytest.mark.asyncio
    async def test_health_check_implementation_error(self):
        """Test health check with implementation error."""
        service = ErrorInHealthCheckService()
        await service.start()
        
        health = await service.check_health()
        assert health["status"] == "error"
        assert "Health check error" in health["error"]
        assert health["service_info"]["error"] == "Health check error"

    @pytest.mark.asyncio
    async def test_stop_implementation_error(self):
        """Test stop with implementation error."""
        service = ErrorInStopService()
        await service.start()
        
        with pytest.raises(ValueError, match="Stop error"):
            await service.stop()
        assert service._error == "Stop error"

    @pytest.mark.asyncio
    async def test_custom_health_check(self):
        """Test custom health check implementation."""
        service = CustomHealthCheckService()
        await service.start()
        
        # Test with custom health data
        custom_data = {"status": "warning", "message": "Custom warning"}
        service.set_health_data(custom_data)
        
        health = await service.check_health()
        assert health["status"] == "warning"
        assert health["message"] == "Custom warning"
        
        # Test with error in custom data
        error_data = {"error": "Custom error"}
        service.set_health_data(error_data)
        
        health = await service.check_health()
        assert health["status"] == "error"
        assert health["error"] == "Custom error"
        
        # Test with invalid custom data
        invalid_data = {"invalid": "data"}
        service.set_health_data(invalid_data)
        
        health = await service.check_health()
        assert health["status"] == "error"
        assert "Invalid health check data" in health["error"]

    @pytest.mark.asyncio
    async def test_empty_implementations(self):
        """Test empty implementations of _start, _stop, and _check_health."""
        service = BaseService("test_service")
        
        # Test _start
        await service._start()  # Should do nothing
        
        # Test _stop
        await service._stop()  # Should do nothing
        
        # Test _check_health when not initialized
        with pytest.raises(RuntimeError, match="Service not initialized"):
            await service._check_health()
            
        # Test _check_health when initialized
        service._is_initialized = True
        result = await service._check_health()
        assert result == {}
