"""Base test fixtures."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_router import BaseRouter
from micro_cold_spray.api.base.base_registry import register_service


class MockBaseService(BaseService):
    """Mock base service for testing."""

    async def _start(self) -> None:
        """Start the service."""
        pass

    async def _stop(self) -> None:
        """Stop the service."""
        pass


@pytest.fixture
async def base_service():
    """Create base service fixture."""
    service = MockBaseService("test_service")
    register_service(service)
    await service.start()
    yield service
    await service.stop()


@pytest.fixture
def test_app():
    """Create test app fixture."""
    app = FastAPI()
    router = BaseRouter(service_class=MockBaseService)
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def test_app_with_cors():
    """Create test app with CORS enabled."""
    app = FastAPI()
    router = BaseRouter(service_class=MockBaseService)
    app.include_router(router)
    return TestClient(app)
