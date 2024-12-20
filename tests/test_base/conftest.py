"""Test fixtures for base tests."""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from tests.fixtures.base import MockBaseService


@pytest.fixture
async def test_app():
    """Create test app fixture."""
    from micro_cold_spray.api.base.base_app import BaseApp
    app = BaseApp(
        service_class=MockBaseService,
        title="Test API",
        service_name="test"
    )
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def async_client(test_app: FastAPI):
    """Create async test client fixture."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
