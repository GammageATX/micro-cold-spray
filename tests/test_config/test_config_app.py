"""Tests for configuration application."""

import pytest
from pathlib import Path
from fastapi import FastAPI

from micro_cold_spray.api.config.config_app import ConfigApp, create_app
from micro_cold_spray.api.config.config_service import ConfigService

# Import base fixtures and utilities
from tests.test_config.config_test_base import (
    create_test_app,
    create_test_client
)
# Import fixtures but don't redefine them
from tests.fixtures.base import test_app_with_cors  # noqa: F401
from tests.test_config.conftest import config_base_service  # noqa: F401


def test_create_app(test_app_with_cors):
    """Test app creation.
    
    Args:
        test_app_with_cors: Base app fixture with CORS
    """
    app = create_app()
    assert isinstance(app, FastAPI)
    assert isinstance(app, ConfigApp)
    assert app.title == "Configuration Service"


def test_app_initialization(config_app, config_base_service):
    """Test app initialization.
    
    Args:
        config_app: Config app fixture
        config_base_service: Base config service fixture
    """
    assert config_app.title == "Configuration Service"
    assert config_app.service_name == "config"
    assert config_app.service_class == ConfigService
    assert config_app.enable_cors is True
    assert config_app.enable_metrics is True


def test_app_with_config_dir():
    """Test app initialization with config directory."""
    config_dir = Path("test_config")
    app = create_test_app(ConfigService)
    app.config_dir = config_dir
    assert app.title == "Configuration Service"
    assert app.service_name == "config"


def test_app_routes(config_app):
    """Test app routes are properly configured.
    
    Args:
        config_app: Config app fixture
    """
    routes = [route.path for route in config_app.routes]
    assert "/config" in routes
    assert "/health" in routes
    assert "/metrics" in routes


def test_app_middleware(config_app):
    """Test app middleware is properly configured.
    
    Args:
        config_app: Config app fixture
    """
    middleware = [m.cls.__name__ for m in config_app.user_middleware]
    assert "CORSMiddleware" in middleware
    assert "GZipMiddleware" in middleware


def test_app_health_endpoint(test_client):
    """Test health endpoint.
    
    Args:
        test_client: FastAPI test client
    """
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "service_info" in data
    assert data["service_info"]["name"] == "config"


def test_app_metrics_endpoint(test_client):
    """Test metrics endpoint.
    
    Args:
        test_client: FastAPI test client
    """
    response = test_client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
