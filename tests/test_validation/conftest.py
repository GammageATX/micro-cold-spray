"""Test fixtures for validation tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
from httpx import ASGITransport

from micro_cold_spray.api.validation.router import router, init_router
from micro_cold_spray.api.validation.service import ValidationService
from micro_cold_spray.api.base.router import add_health_endpoints


@pytest.fixture
def mock_validation_service():
    """Create a mock validation service."""
    service = MagicMock(spec=ValidationService)
    service.is_running = True
    service.start_time = datetime.now()
    service._service_name = "validation"
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
        "active_validations": 0,
        "total_validations": 0,
        "failed_validations": 0
    })
    service.validate = AsyncMock(return_value=True)
    service.get_validation_rules = AsyncMock(return_value=["rule1", "rule2"])
    service.add_validation_rule = AsyncMock()
    service.remove_validation_rule = AsyncMock()
    
    return service


@pytest.fixture
def app(mock_validation_service):
    """Create FastAPI test application."""
    app = FastAPI()
    init_router(mock_validation_service)
    add_health_endpoints(app, mock_validation_service)
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
