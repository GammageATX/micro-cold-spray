"""Test fixtures for messaging tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
from httpx import ASGITransport

from micro_cold_spray.api.messaging.router import router, init_router
from micro_cold_spray.api.messaging.service import MessagingService
from micro_cold_spray.api.base.router import add_health_endpoints


@pytest.fixture
def mock_messaging_service():
    """Create a mock messaging service."""
    service = MagicMock(spec=MessagingService)
    service.is_running = True
    service.start_time = datetime.now()
    service._service_name = "messaging"
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
        "topics": 4,
        "active_subscribers": 2,
        "background_tasks": 1,
        "queue_size": 0
    })
    service.get_topics = AsyncMock(return_value={"topic1", "topic2", "topic3", "topic4"})
    service.get_subscriber_count = AsyncMock(return_value=2)
    service.publish = AsyncMock()
    service.request = AsyncMock()
    service.subscribe = AsyncMock()
    service.set_valid_topics = AsyncMock()
    
    return service


@pytest.fixture
def app(mock_messaging_service):
    """Create FastAPI test application."""
    app = FastAPI()
    init_router(mock_messaging_service)
    add_health_endpoints(app, mock_messaging_service)
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
