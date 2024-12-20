"""Test base app module."""

import pytest
from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from micro_cold_spray.api.base.base_app import BaseApp
from micro_cold_spray.api.base.base_errors import create_error
from tests.conftest import MockBaseService


@pytest.fixture
def test_model():
    """Create test model class."""
    class TestModel(BaseModel):
        """Test model."""
        value: int = Field(ge=0)
    return TestModel


class TestBaseApp:
    """Test base app."""

    @pytest.mark.asyncio
    async def test_init(self, test_app: FastAPI):
        """Test app initialization."""
        assert test_app.state.service is not None
        assert test_app.state.service.is_running

    @pytest.mark.asyncio
    async def test_cors_enabled(self, test_app: FastAPI, async_client):
        """Test CORS middleware."""
        response = await async_client.options(
            "/health",
            headers={
                "Origin": "http://testserver",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "*"
        assert "DELETE" in response.headers["access-control-allow-methods"]
        assert "GET" in response.headers["access-control-allow-methods"]
        assert "POST" in response.headers["access-control-allow-methods"]
        assert "PUT" in response.headers["access-control-allow-methods"]
        assert "PATCH" in response.headers["access-control-allow-methods"]
        assert response.headers["access-control-allow-headers"] == "Content-Type"

    @pytest.mark.asyncio
    async def test_logging_middleware(self, test_app: FastAPI, async_client):
        """Test logging middleware."""
        response = await async_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_service_start_failure(self):
        """Test service start failure."""
        class FailingService(MockBaseService):
            async def start(self):
                self._is_running = False

        app = BaseApp(
            service_class=FailingService,
            title="Test App",
            service_name="test"
        )

        with pytest.raises(Exception) as exc:
            async with app.router.lifespan_context(app):
                pass
        error = exc.value
        assert isinstance(error, Exception)
        assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert error.detail["message"] == "test service failed to start"

    @pytest.mark.asyncio
    async def test_service_stop_error(self):
        """Test service stop error."""
        class ErrorService(MockBaseService):
            async def stop(self):
                raise ValueError("Test error")

        app = BaseApp(
            service_class=ErrorService,
            title="Test App",
            service_name="test"
        )

        async with app.router.lifespan_context(app):
            assert app.state.service is not None
            assert app.state.service.is_running

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, test_app: FastAPI, async_client, test_model):
        """Test validation error handling."""
        @test_app.post("/validate")
        async def validate_endpoint(data: test_model):
            return data

        response = await async_client.post("/validate", json={"value": -1})
        assert response.status_code == 422
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_error_handling(self, test_app: FastAPI, async_client):
        """Test error handling."""
        @test_app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        response = await async_client.get("/error")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert data["detail"]["message"] == "Test error"
        assert data["detail"]["context"]["path"] == "/error"
        assert "timestamp" in data["detail"]

    @pytest.mark.asyncio
    async def test_handle_non_validation_error(self, test_app: FastAPI, async_client):
        """Test handling of non-validation errors."""
        @test_app.get("/custom-error")
        async def custom_error_endpoint():
            class CustomError(Exception):
                pass
            raise CustomError("Custom test error")

        response = await async_client.get("/custom-error")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert data["detail"]["message"] == "Custom test error"
        assert data["detail"]["context"]["path"] == "/custom-error"
        assert "timestamp" in data["detail"]
