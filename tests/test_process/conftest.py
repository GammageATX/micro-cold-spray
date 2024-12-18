"""Test fixtures for process tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
from httpx import ASGITransport

from micro_cold_spray.api.process.router import router, init_router
from micro_cold_spray.api.process.service import ProcessService
from micro_cold_spray.api.base.router import add_health_endpoints


@pytest.fixture
def mock_process_service():
    """Create a mock process service."""
    service = MagicMock(spec=ProcessService)
    service.is_running = True
    service.start_time = datetime.now()
    service._service_name = "process"
    service.version = "1.0.0"
    
    # Define uptime property getter
    def get_uptime(self):
        if not self.is_running or self.start_time is None:
            return None
        return (datetime.now() - self.start_time).total_seconds()
    
    # Set uptime as a property
    type(service).uptime = property(get_uptime)
    
    # Mock async methods
    service.start = AsyncMock()
    service.stop = AsyncMock()
    service.check_health = AsyncMock(return_value={
        "status": "ok",
        "active_processes": 0,
        "completed_processes": 0,
        "failed_processes": 0,
        "current_process": None
    })
    service.start_process = AsyncMock()
    service.stop_process = AsyncMock()
    service.get_process_status = AsyncMock(return_value="idle")
    service.get_process_history = AsyncMock(return_value=[])
    service.clear_history = AsyncMock()
    
    return service


@pytest.fixture
def app(mock_process_service):
    """Create FastAPI test application."""
    app = FastAPI()
    init_router(mock_process_service)
    add_health_endpoints(app, mock_process_service)
    app.include_router(router)
    return app


@pytest.fixture
def test_client(app):
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app):
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
