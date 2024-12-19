"""Test fixtures for communication tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
from httpx import ASGITransport

from micro_cold_spray.api.communication.router import router
from micro_cold_spray.api.communication.service import CommunicationService
from micro_cold_spray.api.base.router import add_health_endpoints


@pytest.fixture
def mock_communication_service():
    """Create a mock communication service."""
    service = MagicMock(spec=CommunicationService)
    service.is_running = True
    service.start_time = datetime.now()
    service._service_name = "communication"
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
        "service_info": {
            "name": "communication",
            "version": "1.0.0",
            "running": True,
            "uptime": "0:00:00"
        },
        "components": {
            "plc": True,
            "ssh": True,
            "equipment": True,
            "feeder": True,
            "motion": True,
            "tag_cache": True,
            "tag_mapping": True
        },
        "details": None
    })
    service.connect = AsyncMock()
    service.disconnect = AsyncMock()
    service.send = AsyncMock()
    service.receive = AsyncMock()
    service.get_connection_status = AsyncMock(return_value=True)
    
    return service


@pytest.fixture
def app(mock_communication_service):
    """Create FastAPI test application."""
    app = FastAPI()
    # Store service in app state for dependency injection
    app.state.service = mock_communication_service
    add_health_endpoints(app, mock_communication_service)
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
