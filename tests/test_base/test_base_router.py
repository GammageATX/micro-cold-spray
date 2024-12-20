"""Test base router module."""

import pytest
from fastapi import status, Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from micro_cold_spray.api.base.base_router import BaseRouter
from tests.conftest import MockBaseService


@pytest.fixture
async def router(test_app: FastAPI):
    """Create test router."""
    router = BaseRouter()
    test_app.router = router
    yield router


@pytest.fixture
async def base_service():
    """Create test service."""
    service = MockBaseService()
    yield service
    try:
        await service.stop()
    except Exception:
        pass  # Ignore stop errors in teardown


class TestBaseRouter:
    """Test base router."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, test_app: FastAPI, async_client):
        """Test health check endpoint."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["is_healthy"] is True
        assert data["status"] == "running"
        assert "services" in data["context"]

    @pytest.mark.asyncio
    async def test_health_check_with_service(self, test_app: FastAPI, async_client, base_service, router):
        """Test health check with service."""
        router.services.append(base_service)
        await base_service.start()
        
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["is_healthy"] is True
        assert data["status"] == "running"
        assert len(data["context"]["services"]) == 1
        assert data["context"]["services"][0]["is_healthy"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_failing_service(self, test_app: FastAPI, async_client, base_service, router):
        """Test health check with failing service."""
        router.services.append(base_service)
        base_service._is_running = False
        
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["is_healthy"] is False
        assert data["status"] == "error"
        assert len(data["context"]["services"]) == 1
        assert data["context"]["services"][0]["is_healthy"] is False

    @pytest.mark.asyncio
    async def test_health_check_with_error(self, test_app: FastAPI, async_client, router):
        """Test health check with service that raises error."""
        class ErrorService(MockBaseService):
            async def health(self):
                raise ValueError("Test error")

        service = ErrorService()
        router.services.append(service)
        
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["is_healthy"] is False
        assert data["status"] == "error"
        assert len(data["context"]["services"]) == 1
        assert data["context"]["services"][0]["is_healthy"] is False
        assert "Test error" in data["context"]["services"][0]["context"]["error"]

    @pytest.mark.asyncio
    async def test_router_error_handling(self, test_app: FastAPI, async_client):
        """Test error handling."""
        @test_app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        response = await async_client.get("/error")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert data["detail"]["message"] == "Test error"
        assert "timestamp" in data["detail"]

    @pytest.mark.asyncio
    async def test_router_validation_error(self, test_app: FastAPI, async_client):
        """Test validation error handling."""
        class TestModel(BaseModel):
            value: int = Field(ge=0)

        @test_app.post("/validate")
        async def validate_endpoint(data: TestModel):
            return data

        response = await async_client.post("/validate", json={"value": -1})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any(
            "greater than or equal to 0" in error["msg"]
            for error in data["detail"]
        )
