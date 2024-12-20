"""Test base app module."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from micro_cold_spray.api.base.base_app import BaseApp
from tests.conftest import MockBaseService


@pytest.fixture
def app():
    """Create test app."""
    return BaseApp(
        service_class=MockBaseService,
        title="Test API",
        service_name="test_service"
    )


@pytest.fixture
def app_with_cors():
    """Create test app with CORS enabled."""
    return BaseApp(
        service_class=MockBaseService,
        title="Test API",
        service_name="test_service",
        enable_cors=True
    )


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def client_with_cors(app_with_cors):
    """Create test client with CORS."""
    return TestClient(app_with_cors)


class TestBaseApp:
    """Test base app functionality."""

    def test_init(self, app):
        """Test app initialization."""
        assert isinstance(app, FastAPI)
        assert app.service_class == MockBaseService
        assert app.service_name == "test_service"

    def test_cors_enabled(self, client_with_cors):
        """Test CORS middleware is enabled."""
        response = client_with_cors.options(
            "/health",
            headers={
                "Origin": "http://testserver",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "*"

    def test_logging_middleware(self, client, caplog):
        """Test logging middleware."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "HTTP Request: GET" in caplog.text
