"""Tests for base service functionality."""

import pytest
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
        assert service.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test service start/stop lifecycle."""
        service = BaseService("test_service")
        
        # Test start
        await service.start()
        assert service.is_running
        assert service._is_initialized
        
        # Test duplicate start
        await service.start()  # Should just log warning
        
        # Test stop
        await service.stop()
        assert not service.is_running
        
        # Test duplicate stop
        await service.stop()  # Should just log warning

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
            
        # Force service into running state to test stop error
        service._is_running = True
        
        # Test stop error
        with pytest.raises(ValueError, match="Stop error"):
            await service.stop()
