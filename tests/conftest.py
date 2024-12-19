"""Global test fixtures and configuration."""

import pytest
from enum import IntEnum, auto
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Test execution order
class TestOrder(IntEnum):
    """Test execution order enumeration."""
    UNIT = auto()
    INTEGRATION = auto()
    API = auto()

def order(value: TestOrder):
    """Decorator to set test execution order."""
    def _order(cls):
        cls.order = value
        return cls
    return _order

@pytest.fixture
def mock_base_service():
    """Create a mock base service with common functionality."""
    service = MagicMock()
    service.is_running = True
    service.start_time = datetime.now()
    service.version = "1.0.0"
    service._service_name = "test_service"
    
    # Mock async methods
    service.start = AsyncMock()
    service.stop = AsyncMock()
    service.check_health = AsyncMock(return_value={"status": "ok"})
    
    return service

@pytest.fixture
def mock_config():
    """Create mock configuration data."""
    return {
        "application": {
            "name": "micro-cold-spray",
            "version": "1.0.0",
            "settings": {
                "log_level": "INFO",
                "debug_mode": False
            }
        }
    }
  