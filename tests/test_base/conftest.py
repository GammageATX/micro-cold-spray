"""Base-specific test fixtures."""

import pytest
from contextlib import asynccontextmanager
from fastapi import FastAPI

from tests.conftest import MockBaseService
from micro_cold_spray.api.base import BaseApp


@pytest.fixture
def test_app(base_service: MockBaseService) -> FastAPI:
    """Create test app with base service."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
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
def test_app_with_cors(base_service: MockBaseService) -> FastAPI:
    """Create test app with CORS enabled."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
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
