"""Test base router module."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from micro_cold_spray.api.base.base_app import create_app
from micro_cold_spray.api.base.base_router import BaseRouter
from tests.test_base.conftest import (
    TestModel,
    TestRouterService,
    ErrorRouterService
)


def test_router_health():
    """Test router health check."""
    app = create_app(
        service_class=TestRouterService,
        title="Test API"
    )
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "is_healthy" in data
        assert "services" in data
        assert isinstance(data["services"], list)
        assert len(data["services"]) == 1
        assert data["services"][0]["is_healthy"]
        assert data["services"][0]["status"] == "running"
        assert data["services"][0]["service"] == "testrouterservice"


def test_router_error():
    """Test router error handling."""
    app = create_app(
        service_class=ErrorRouterService,
        title="Test API"
    )
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert not data["is_healthy"]
        assert len(data["services"]) == 1
        service = data["services"][0]
        assert not service["is_healthy"]
        assert service["status"] == "error"
        assert "error" in service
        assert "Health check failed" in service["error"]


def test_router_multiple_services():
    """Test router with multiple services."""
    app = create_app(
        service_class=TestRouterService,
        title="Test API"
    )
    router = BaseRouter()
    router.services.append(app.state.service)
    error_service = ErrorRouterService()
    router.services.append(error_service)
    app.include_router(router)
    
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert not data["is_healthy"]  # One service failed
        assert len(data["services"]) == 2
        # First service healthy
        assert data["services"][0]["is_healthy"]
        assert data["services"][0]["status"] == "running"
        # Second service error
        assert not data["services"][1]["is_healthy"]
        assert data["services"][1]["status"] == "error"
        assert "error" in data["services"][1]


def test_router_validation():
    """Test router validation."""
    app = create_app(
        service_class=TestRouterService,
        title="Test API"
    )
    
    @app.post("/test")
    async def test_endpoint(model: TestModel):
        return model

    with TestClient(app) as client:
        # Valid request
        response = client.post("/test", json={
            "id": 1,
            "name": "test",
            "value": 42.0
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "test"
        assert data["value"] == 42.0

        # Invalid request - wrong type
        response = client.post("/test", json={
            "id": "not_an_int",
            "name": "test",
            "value": -1.0
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert data["detail"][0]["type"] == "int_parsing"

        # Invalid request - missing field
        response = client.post("/test", json={
            "id": 1,
            "value": 42.0
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert "name" in data["detail"][0]["loc"]
