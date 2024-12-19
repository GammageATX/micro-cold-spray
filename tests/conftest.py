"""Global test fixtures and configuration."""

import pytest
from enum import IntEnum, auto
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
import httpx
from httpx import ASGITransport


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


# Main application fixtures
@pytest.fixture
def app(mock_base_service) -> FastAPI:
    """Create main FastAPI application for testing."""
    app = FastAPI(title="Micro Cold Spray API", version="1.0.0")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize services
    app.state.service = mock_base_service
    
    return app


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# Mock fixtures
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
    service.check_health = AsyncMock(return_value={
        "status": "ok",
        "service_info": {
            "name": "test_service",
            "version": "1.0.0",
            "running": True,
            "ready": True,
            "uptime": 0
        }
    })
    
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
        },
        "services": {
            "ui": {
                "host": "localhost",
                "port": 8000
            },
            "api": {
                "host": "localhost",
                "port": 8001
            }
        }
    }


@pytest.fixture
def mock_service_registry():
    """Create mock service registry."""
    registry = MagicMock()
    registry.get_service.return_value = None
    registry.register_service = AsyncMock()
    registry.unregister_service = AsyncMock()
    return registry


@pytest.fixture
def mock_error_handler():
    """Create mock error handler."""
    handler = MagicMock()
    handler.handle_error = AsyncMock()
    handler.format_error = MagicMock(return_value={"detail": "Test error"})
    return handler
