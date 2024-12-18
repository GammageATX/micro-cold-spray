"""Test fixtures for state tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
from httpx import ASGITransport

from micro_cold_spray.api.state.router import router, init_router
from micro_cold_spray.api.state.service import StateService
from micro_cold_spray.api.base.router import add_health_endpoints


@pytest.fixture
def mock_state_service():
    """Create a mock state service."""
    service = MagicMock(spec=StateService)
    service.is_running = True
    service.start_time = datetime.now()
    service._service_name = "state"
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
        "current_state": "idle",
        "transitions": 0,
        "last_transition": None
    })
    service.get_state = AsyncMock(return_value="idle")
    service.set_state = AsyncMock()
    service.can_transition = AsyncMock(return_value=True)
    service.get_valid_transitions = AsyncMock(return_value=["idle", "running", "paused"])
    
    return service


@pytest.fixture
def app(mock_state_service):
    """Create FastAPI test application."""
    app = FastAPI()
    init_router(mock_state_service)
    add_health_endpoints(app, mock_state_service)
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
