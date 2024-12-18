"""Test fixtures for data collection tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
from httpx import ASGITransport

from micro_cold_spray.api.data_collection.router import router, init_router
from micro_cold_spray.api.data_collection.service import DataCollectionService
from micro_cold_spray.api.base.router import add_health_endpoints


@pytest.fixture
def mock_data_collection_service():
    """Create a mock data collection service."""
    service = MagicMock(spec=DataCollectionService)
    service.is_running = True
    service.start_time = datetime.now()
    service._service_name = "data_collection"
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
        "active_collectors": 2,
        "total_samples": 1000,
        "sample_rate": 100,
        "buffer_usage": 0.5
    })
    service.start_collection = AsyncMock()
    service.stop_collection = AsyncMock()
    service.get_data = AsyncMock(return_value=[])
    service.clear_data = AsyncMock()
    service.get_collection_status = AsyncMock(return_value=True)
    
    return service


@pytest.fixture
def app(mock_data_collection_service):
    """Create FastAPI test application."""
    app = FastAPI()
    init_router(mock_data_collection_service)
    add_health_endpoints(app, mock_data_collection_service)
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
