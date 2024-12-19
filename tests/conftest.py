"""Root test configuration and shared fixtures."""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from datetime import datetime
from unittest.mock import AsyncMock, PropertyMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx

from micro_cold_spray.api.base import BaseService


# Use loop_scope instead of scope
pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async test client."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_base_service() -> AsyncMock:
    """Create a mock base service."""
    service = AsyncMock(spec=BaseService)
    type(service).is_initialized = PropertyMock(return_value=True)
    type(service).is_running = PropertyMock(return_value=True)
    type(service)._service_name = PropertyMock(return_value="MockService")
    type(service).version = PropertyMock(return_value="1.0.0")
    type(service).uptime = PropertyMock(return_value="0:00:00")
    
    async def mock_check_health():
        return {
            "status": "ok",
            "service_info": {
                "name": "MockService",
                "version": "1.0.0",
                "running": True,
                "uptime": "0:00:00",
                "metrics": {
                    "start_count": 1,
                    "stop_count": 0,
                    "error_count": 0
                }
            }
        }
    service.check_health = AsyncMock(side_effect=mock_check_health)
    return service


@pytest.fixture
def mock_app(mock_base_service: AsyncMock) -> FastAPI:
    """Create FastAPI test app with mock service."""
    app = FastAPI()
    app.state.service = mock_base_service
    return app


@pytest.fixture(autouse=True)
def setup_logging(caplog: pytest.LogCaptureFixture) -> None:
    """Set up logging for tests."""
    import logging
    caplog.set_level(logging.INFO)


@pytest.fixture
def mock_datetime(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Mock datetime for consistent timestamps."""
    FAKE_TIME = datetime(2023, 1, 1, 12, 0, 0)
    
    class MockDatetime:
        @classmethod
        def now(cls):
            return FAKE_TIME
            
    monkeypatch.setattr("datetime.datetime", MockDatetime)
    return FAKE_TIME
