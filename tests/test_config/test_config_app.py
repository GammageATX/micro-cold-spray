"""Tests for configuration application."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from pathlib import Path

from micro_cold_spray.api.config.config_app import ConfigApp
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.base.base_errors import create_error
from tests.test_config.conftest import BaseConfigTest


class TestConfigApp(BaseConfigTest):
    """Test configuration application."""

    @pytest.fixture
    def test_model(self):
        """Create test model class."""
        class TestModel(BaseModel):
            """Test model."""
            value: int = Field(ge=0)
        return TestModel

    @pytest.mark.asyncio
    async def test_init(self, test_app):
        """Test app initialization."""
        assert test_app.state.service is not None
        assert test_app.state.service.is_running
        assert test_app.state.service.service_name == "config"

    @pytest.mark.asyncio
    async def test_cors_enabled(self, test_app, async_client):
        """Test CORS middleware."""
        response = await async_client.options(
            "/health",
            headers={
                "Origin": "http://testserver",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )
        self.verify_config_response(response, status.HTTP_200_OK)
        assert response.headers["access-control-allow-origin"] == "*"
        assert "DELETE" in response.headers["access-control-allow-methods"]
        assert "GET" in response.headers["access-control-allow-methods"]
        assert "POST" in response.headers["access-control-allow-methods"]
        assert "PUT" in response.headers["access-control-allow-methods"]
        assert "PATCH" in response.headers["access-control-allow-methods"]
        assert response.headers["access-control-allow-headers"] == "Content-Type"

    @pytest.mark.asyncio
    async def test_logging_middleware(self, test_app, async_client):
        """Test logging middleware."""
        response = await async_client.get("/health")
        self.verify_config_response(response, status.HTTP_200_OK)

    @pytest.mark.asyncio
    async def test_service_start_failure(self):
        """Test service start failure."""
        class FailingService(ConfigService):
            async def start(self):
                self._is_running = False
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Failed to start service"
                )

        app = ConfigApp(service_class=FailingService)
        
        with pytest.raises(Exception) as exc:
            async with app.router.lifespan_context(app):
                pass
        self.verify_error_response(
            exc,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Failed to start service"
        )

    @pytest.mark.asyncio
    async def test_service_stop_error(self):
        """Test service stop error."""
        class ErrorService(ConfigService):
            async def stop(self):
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Failed to stop service"
                )

        app = ConfigApp(service_class=ErrorService)
        
        with pytest.raises(Exception) as exc:
            async with app.router.lifespan_context(app):
                assert app.state.service is not None
                assert app.state.service.is_running
        self.verify_error_response(
            exc,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Failed to stop service"
        )

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, test_app, async_client, test_model):
        """Test validation error handling."""
        @test_app.post("/validate")
        async def validate_endpoint(data: test_model):
            return data

        response = await async_client.post("/validate", json={"value": -1})
        self.verify_config_response(response, status.HTTP_422_UNPROCESSABLE_ENTITY)
        data = response.json()
        assert "detail" in data
        assert any("greater than or equal to 0" in error["msg"] for error in data["detail"])

    @pytest.mark.asyncio
    async def test_error_handling(self, test_app, async_client):
        """Test error handling."""
        @test_app.get("/error")
        async def error_endpoint():
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Test error"
            )

        response = await async_client.get("/error")
        self.verify_config_response(response, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()
        assert data["detail"]["message"] == "Test error"
        assert "timestamp" in data["detail"]

    @pytest.mark.asyncio
    async def test_health_check_error(self, test_app, async_client):
        """Test health check with error."""
        mock_service = AsyncMock()
        mock_service.check_health.side_effect = lambda: create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Health check failed"
        )
        test_app.state.service = mock_service

        response = await async_client.get("/health")
        self.verify_config_response(response, status.HTTP_503_SERVICE_UNAVAILABLE)
        data = response.json()
        assert "Health check failed" in data["detail"]["message"]

    @pytest.mark.asyncio
    async def test_metrics_enabled(self):
        """Test metrics endpoint when enabled."""
        app = ConfigApp(enable_metrics=True)
        client = TestClient(app)
        response = client.get("/metrics")
        self.verify_config_response(response, status.HTTP_200_OK)
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    @pytest.mark.asyncio
    async def test_metrics_disabled(self):
        """Test metrics endpoint when disabled."""
        app = ConfigApp(enable_metrics=False)
        client = TestClient(app)
        response = client.get("/metrics")
        self.verify_config_response(response, status.HTTP_404_NOT_FOUND)

    def verify_config_response(self, response, expected_status):
        """Verify configuration response."""
        assert response.status_code == expected_status
