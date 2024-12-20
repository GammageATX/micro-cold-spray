"""Root test configuration and shared fixtures."""

import pytest
from typing import AsyncGenerator
from datetime import datetime
from fastapi import FastAPI
import httpx

from micro_cold_spray.api.base import BaseService


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async test client."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


class MockBaseService(BaseService):
    """Mock base service for testing."""

    def __init__(self, name: str = None):
        """Initialize test service."""
        super().__init__(name or "test_service")
        self._is_running = False

    async def _start(self) -> None:
        """Start the service."""
        self._is_running = True

    async def _stop(self) -> None:
        """Stop the service."""
        self._is_running = False

    @property
    def metrics(self):
        """Get service metrics."""
        return {"test_metric": 123}


@pytest.fixture
def base_service():
    """Create base service fixture."""
    return MockBaseService()


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
