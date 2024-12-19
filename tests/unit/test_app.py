"""Tests for main application."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from micro_cold_spray.__main__ import app


class TestMainApplication:
    """Test cases for main FastAPI application."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_app_configuration(self):
        """Test main application configuration."""
        assert isinstance(app, FastAPI)
        assert app.title == "Micro Cold Spray Control System"
        assert app.version == "1.0.0"
    
    def test_cors_middleware(self, client):
        """Test CORS middleware configuration."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "*"
        assert response.headers["access-control-allow-methods"] == "*"
        assert response.headers["access-control-allow-headers"] == "*"
    
    def test_service_mounting(self):
        """Test service applications are mounted correctly."""
        routes = [route.path for route in app.routes]
        
        # Check API routes
        assert "/api/config" in routes
        assert "/api/communication" in routes
        assert "/api/process" in routes
        assert "/api/state" in routes
        assert "/api/data" in routes
        assert "/api/validation" in routes
        assert "/api/messaging" in routes
        
        # Check UI route
        assert "/ui" in routes
