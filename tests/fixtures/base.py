"""Base test fixtures."""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from contextlib import asynccontextmanager

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_app import BaseApp


class MockBaseService(BaseService):
    """Mock base service for testing."""
    
    async def _start(self) -> None:
        """Start implementation."""
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop implementation."""
        self._is_running = False


@pytest.fixture
async def test_app():
    """Create test app fixture.
    
    Returns:
        FastAPI: Test application instance
    """
    app = BaseApp(
        service_class=MockBaseService,
        title="Test API",
        service_name="test"
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await app.router.startup()
        yield app
        await app.router.shutdown()

    app.router.lifespan_context = lifespan
    
    async with lifespan(app) as test_app:
        yield test_app


@pytest.fixture
async def async_client(test_app: FastAPI):
    """Create async test client fixture.
    
    Args:
        test_app: FastAPI test application
        
    Returns:
        AsyncClient: Async HTTP test client
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
