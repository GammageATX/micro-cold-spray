"""Base-specific test fixtures."""

import pytest
from typing import AsyncGenerator
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.testclient import TestClient

from micro_cold_spray.api.base import BaseService, BaseApp


class TestService(BaseService):
    """Test service for base app testing."""

    def __init__(self, name: str = None):
        """Initialize test service."""
        super().__init__(name or "test_service")
        self._is_running = True

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
    """Create a base service for testing."""
    return TestService()


@pytest.fixture
def test_app(base_service: BaseService) -> FastAPI:
    """Create test app with base service."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Register service without starting it
        app.state.service = base_service
        yield

    app = BaseApp(
        service_class=type(base_service),
        title="Test API",
        service_name="test_service"
    )
    app.router.lifespan = lifespan
    return app


@pytest.fixture
def test_app_with_cors(base_service: BaseService) -> FastAPI:
    """Create test app with CORS enabled."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Register service without starting it
        app.state.service = base_service
        yield

    app = BaseApp(
        service_class=type(base_service),
        title="Test API",
        service_name="test_service",
        enable_cors=True
    )
    app.router.lifespan = lifespan
    return app
