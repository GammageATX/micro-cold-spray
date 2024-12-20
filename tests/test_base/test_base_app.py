"""Test base application module."""

import pytest
from fastapi import FastAPI, status
from pydantic import BaseModel, Field

from micro_cold_spray.api.base.base_app import BaseApp
from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import create_error


class TestModel(BaseModel):
    """Test validation model."""
    value: int = Field(ge=0)


class FailingService(BaseService):
    """Service that fails to start."""
    
    async def _start(self) -> None:
        """Start implementation that fails."""
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Service failed to start",
            context={"service": self.name}
        )


class ErrorService(BaseService):
    """Service that raises error on stop."""
    
    async def _start(self) -> None:
        """Start implementation."""
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop implementation that fails."""
        raise ValueError("Stop failed")


class TestBaseApp:
    """Test base application."""

    @pytest.mark.asyncio
    async def test_app_init(self, test_app: FastAPI):
        """Test app initialization."""
        assert test_app.state.service is not None
        assert test_app.state.service.is_running
        assert test_app.state.service.name == "test"

    @pytest.mark.asyncio
    async def test_cors_middleware(self, async_client):
        """Test CORS middleware."""
        response = await async_client.options(
            "/health",
            headers={
                "Origin": "http://testserver",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["access-control-allow-origin"] == "*"
        assert "DELETE" in response.headers["access-control-allow-methods"]
        assert "GET" in response.headers["access-control-allow-methods"]
        assert "POST" in response.headers["access-control-allow-methods"]
        assert "PUT" in response.headers["access-control-allow-methods"]
        assert "PATCH" in response.headers["access-control-allow-methods"]
        assert response.headers["access-control-allow-headers"] == "*"

    @pytest.mark.asyncio
    async def test_service_start_failure(self):
        """Test service start failure."""
        app = BaseApp(
            service_class=FailingService,
            title="Test API",
            service_name="test"
        )

        with pytest.raises(Exception) as exc:
            async with app.router.lifespan_context(app):
                pass
        assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "failed to start" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == "test"

    @pytest.mark.asyncio
    async def test_service_stop_error(self):
        """Test service stop error."""
        app = BaseApp(
            service_class=ErrorService,
            title="Test API",
            service_name="test"
        )

        @app.router.lifespan_context
        async def lifespan(app: FastAPI):
            await app.router.startup()
            yield
            await app.router.shutdown()

        async with lifespan(app):
            assert app.state.service is not None
            assert app.state.service.is_running

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, test_app: FastAPI, async_client):
        """Test validation error handling."""
        @test_app.post("/validate")
        async def validate_endpoint(data: TestModel):
            return data

        response = await async_client.post("/validate", json={"value": -1})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        assert any("greater than or equal to 0" in error["msg"] for error in data["detail"])

    @pytest.mark.asyncio
    async def test_http_error_handling(self, test_app: FastAPI, async_client):
        """Test HTTP error handling."""
        @test_app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        response = await async_client.get("/error")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"]["message"] == "Test error"
        assert data["detail"]["context"]["path"] == "/error"
        assert "timestamp" in data["detail"]

    @pytest.mark.asyncio
    async def test_request_logging(self, test_app: FastAPI, async_client):
        """Test request logging middleware."""
        @test_app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        response = await async_client.get("/test")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "test"}

    @pytest.mark.asyncio
    async def test_logging_middleware_error(self, test_app: FastAPI, async_client):
        """Test error handling in logging middleware."""
        @test_app.get("/middleware-error")
        async def middleware_error():
            raise ValueError("Middleware error")

        response = await async_client.get("/middleware-error")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Middleware error" in data["detail"]["message"]
        assert data["detail"]["context"]["path"] == "/middleware-error"
