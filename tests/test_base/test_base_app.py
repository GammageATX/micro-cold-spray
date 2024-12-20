"""Test base app module."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import MockBaseService


class TestBaseApp:
    """Test base app functionality."""

    @pytest.mark.asyncio
    async def test_init(self, test_app: FastAPI):
        """Test app initialization."""
        assert isinstance(test_app, FastAPI)
        assert test_app.service_class == MockBaseService
        assert test_app.service_name == "test_service"

    @pytest.mark.asyncio
    async def test_cors_enabled(self, test_app_with_cors: FastAPI, async_client: TestClient):
        """Test CORS middleware is enabled."""
        response = await async_client.options(
            "/health",
            headers={
                "Origin": "http://testserver",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "*"

    @pytest.mark.asyncio
    async def test_logging_middleware(self, test_app: FastAPI, async_client: TestClient, caplog):
        """Test logging middleware."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        assert "HTTP Request: GET" in caplog.text
