"""Test base router module."""

import pytest
from fastapi import status
from pydantic import BaseModel, Field

from micro_cold_spray.api.base.base_router import BaseRouter
from micro_cold_spray.api.base.base_service import BaseService


class TestModel(BaseModel):
    """Test validation model."""
    value: int = Field(ge=0)


class TestService(BaseService):
    """Test service implementation."""
    
    async def _start(self) -> None:
        """Start implementation."""
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop implementation."""
        self._is_running = False


class ErrorService(BaseService):
    """Service that raises errors."""
    
    async def _start(self) -> None:
        """Start implementation."""
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop implementation."""
        self._is_running = False
        
    async def health(self):
        """Health check that raises error."""
        raise ValueError("Health check failed")


class TestBaseRouter:
    """Test base router."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, async_client):
        """Test health check endpoint."""
        response = await async_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_healthy"] is True
        assert data["status"] == "running"
        assert "services" in data["context"]

    @pytest.mark.asyncio
    async def test_health_check_with_service(self, test_app, async_client):
        """Test health check with healthy service."""
        service = TestService()
        test_app.router.services.append(service)
        await service.start()
        
        response = await async_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_healthy"] is True
        assert data["status"] == "running"
        assert len(data["context"]["services"]) == 1
        assert data["context"]["services"][0]["is_healthy"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_stopped_service(self, test_app, async_client):
        """Test health check with stopped service."""
        service = TestService()
        test_app.router.services.append(service)
        
        response = await async_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_healthy"] is False
        assert data["status"] == "error"
        assert len(data["context"]["services"]) == 1
        assert data["context"]["services"][0]["is_healthy"] is False

    @pytest.mark.asyncio
    async def test_health_check_with_error(self, test_app, async_client):
        """Test health check with failing service."""
        service = ErrorService()
        test_app.router.services.append(service)
        await service.start()
        
        response = await async_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_healthy"] is False
        assert data["status"] == "error"
        assert len(data["context"]["services"]) == 1
        assert data["context"]["services"][0]["is_healthy"] is False
        assert "Health check failed" in data["context"]["services"][0]["context"]["error"]

    @pytest.mark.asyncio
    async def test_validation_error(self, test_app, async_client):
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
    async def test_http_error(self, test_app, async_client):
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
    async def test_get_endpoint(self, test_app, async_client):
        """Test GET endpoint."""
        @test_app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        response = await async_client.get("/test")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "test"}

    @pytest.mark.asyncio
    async def test_post_endpoint(self, test_app, async_client):
        """Test POST endpoint."""
        @test_app.post("/test")
        async def test_endpoint(data: dict):
            return data

        test_data = {"message": "test"}
        response = await async_client.post("/test", json=test_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == test_data

    @pytest.mark.asyncio
    async def test_put_endpoint(self, test_app, async_client):
        """Test PUT endpoint."""
        @test_app.put("/test")
        async def test_endpoint(data: dict):
            return data

        test_data = {"message": "test"}
        response = await async_client.put("/test", json=test_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == test_data

    @pytest.mark.asyncio
    async def test_delete_endpoint(self, test_app, async_client):
        """Test DELETE endpoint."""
        @test_app.delete("/test")
        async def test_endpoint():
            return {"message": "deleted"}

        response = await async_client.delete("/test")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "deleted"}

    @pytest.mark.asyncio
    async def test_patch_endpoint(self, test_app, async_client):
        """Test PATCH endpoint."""
        @test_app.patch("/test")
        async def test_endpoint(data: dict):
            return data

        test_data = {"message": "test"}
        response = await async_client.patch("/test", json=test_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == test_data
