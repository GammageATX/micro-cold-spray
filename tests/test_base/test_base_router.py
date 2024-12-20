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


@pytest.fixture
def test_model():
    """Create test model class."""
    class TestModel(BaseModel):
        """Test model."""
        value: int = Field(ge=0)
    return TestModel


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
    async def test_router_validation_error(self, test_app: FastAPI, async_client, test_model):
        """Test validation error handling."""
        @test_app.post("/validate")
        async def validate_endpoint(data: test_model):
            return data

        response = await async_client.post("/validate", json={"value": -1})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any(
            "greater than or equal to 0" in error["msg"]
            for error in data["detail"]
        )

    @pytest.mark.asyncio
    async def test_get_decorator(self, router: BaseRouter, async_client):
        """Test GET decorator."""
        @router.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        response = await async_client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "test"}

    @pytest.mark.asyncio
    async def test_post_decorator(self, router: BaseRouter, async_client):
        """Test POST decorator."""
        @router.post("/test")
        async def test_endpoint(data: dict):
            return data

        test_data = {"message": "test"}
        response = await async_client.post("/test", json=test_data)
        assert response.status_code == 200
        assert response.json() == test_data

    @pytest.mark.asyncio
    async def test_put_decorator(self, router: BaseRouter, async_client):
        """Test PUT decorator."""
        @router.put("/test")
        async def test_endpoint(data: dict):
            return data

        test_data = {"message": "test"}
        response = await async_client.put("/test", json=test_data)
        assert response.status_code == 200
        assert response.json() == test_data

    @pytest.mark.asyncio
    async def test_delete_decorator(self, router: BaseRouter, async_client):
        """Test DELETE decorator."""
        @router.delete("/test")
        async def test_endpoint():
            return {"message": "deleted"}

        response = await async_client.delete("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "deleted"}

    @pytest.mark.asyncio
    async def test_patch_decorator(self, router: BaseRouter, async_client):
        """Test PATCH decorator."""
        @router.patch("/test")
        async def test_endpoint(data: dict):
            return data

        test_data = {"message": "test"}
        response = await async_client.patch("/test", json=test_data)
        assert response.status_code == 200
        assert response.json() == test_data
