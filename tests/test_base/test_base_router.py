"""Test base router module."""

import pytest
from fastapi import status, Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from micro_cold_spray.api.base.base_router import BaseRouter
from tests.conftest import MockBaseService


@pytest.fixture
def router():
    """Create test router."""
    router = BaseRouter()
    router.services = []  # Initialize empty services list
    return router


@pytest.fixture
def client(router):
    """Create test client."""
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)}
        )
        
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)}
        )
    
    @router.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    class TestModel(BaseModel):
        value: int = Field(ge=0)

    @router.post("/validate")
    async def validate_endpoint(data: TestModel):
        return data

    @router.put("/test")
    async def put_endpoint():
        return {"method": "PUT"}

    @router.delete("/test")
    async def delete_endpoint():
        return {"method": "DELETE"}

    @router.patch("/test")
    async def patch_endpoint():
        return {"method": "PATCH"}
        
    app.include_router(router)
    return TestClient(app)


class TestBaseRouter:
    """Test base router."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["is_healthy"] is True
        assert data["status"] == "running"
        assert "services" in data["context"]

    @pytest.mark.asyncio
    async def test_health_check_with_service(self, client, router):
        """Test health check with service."""
        service = MockBaseService()
        service._is_running = True  # Ensure service is running
        router.services.append(service)
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["is_healthy"] is True
        assert data["status"] == "running"
        assert len(data["context"]["services"]) == 1
        assert data["context"]["services"][0]["is_healthy"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_failing_service(self, client, router):
        """Test health check with failing service."""
        service = MockBaseService()
        service._is_running = False
        router.services.append(service)
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["is_healthy"] is False
        assert data["status"] == "error"
        assert len(data["context"]["services"]) == 1
        assert data["context"]["services"][0]["is_healthy"] is False

    @pytest.mark.asyncio
    async def test_health_check_with_error(self, client, router):
        """Test health check with service that raises error."""
        class ErrorService(MockBaseService):
            async def health(self):
                raise ValueError("Test error")

        service = ErrorService()
        router.services.append(service)
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["is_healthy"] is False
        assert data["status"] == "error"
        assert len(data["context"]["services"]) == 1
        assert data["context"]["services"][0]["is_healthy"] is False
        assert "Test error" in data["context"]["services"][0]["context"]["error"]

    @pytest.mark.asyncio
    async def test_router_error_handling(self, client):
        """Test error handling."""
        response = client.get("/error")
        assert response.status_code == 500
        assert "detail" in response.json()
        assert "Test error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_router_validation_error(self, client):
        """Test validation error handling."""
        response = client.post("/validate", json={"value": -1})
        assert response.status_code == 422
        assert "detail" in response.json()
        assert "greater than or equal to 0" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_router_put_method(self, client):
        """Test PUT method."""
        response = client.put("/test")
        assert response.status_code == 200
        assert response.json()["method"] == "PUT"

    @pytest.mark.asyncio
    async def test_router_delete_method(self, client):
        """Test DELETE method."""
        response = client.delete("/test")
        assert response.status_code == 200
        assert response.json()["method"] == "DELETE"

    @pytest.mark.asyncio
    async def test_router_patch_method(self, client):
        """Test PATCH method."""
        response = client.patch("/test")
        assert response.status_code == 200
        assert response.json()["method"] == "PATCH"
