"""Tests for configuration application."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from micro_cold_spray.api.config.config_app import ConfigApp, create_app
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.base.base_exceptions import ConfigError

# Import base test utilities
from tests.test_config.config_test_base import create_test_app, create_test_client
# Import but don't redefine base fixtures
from tests.fixtures.base import test_app_with_cors  # noqa: F401
from tests.test_config.conftest import config_base_service  # noqa: F401


def test_app_initialization():
    """Test app initialization."""
    app = ConfigApp()
    assert app.service_class == ConfigService
    assert app.service_name == "config"
    assert app.enable_metrics is True


def test_app_with_config_dir():
    """Test app initialization with config directory."""
    app = ConfigApp(config_dir="test_config")
    assert app.config_dir == "test_config"


def test_create_app():
    """Test app creation helper."""
    app = create_app()
    assert isinstance(app, ConfigApp)
    assert app.service_class == ConfigService


def test_cors_middleware_enabled():
    """Test CORS middleware configuration when enabled."""
    app = ConfigApp(enable_cors=True)
    assert any(m.cls.__name__ == "CORSMiddleware" for m in app.user_middleware)


def test_app_without_cors():
    """Test app without CORS middleware."""
    app = ConfigApp(enable_cors=False)
    assert not any(m.cls.__name__ == "CORSMiddleware" for m in app.user_middleware)


def test_app_with_metrics():
    """Test metrics endpoint configuration."""
    app = ConfigApp(enable_metrics=True)
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"


def test_app_without_metrics():
    """Test app without metrics endpoint."""
    app = ConfigApp(enable_metrics=False)
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 404


def test_app_health_check():
    """Test health check endpoint."""
    app = ConfigApp()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "service_info" in data


def test_app_error_handling():
    """Test error handling middleware."""
    app = ConfigApp()
    
    # Mock service to raise error
    mock_service = MagicMock()
    mock_service.check_health.side_effect = ConfigError("Test error")
    
    with patch("micro_cold_spray.api.config.config_app.ConfigService", return_value=mock_service):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Test error"
