"""Unit tests for base router functionality."""

import pytest
from fastapi import APIRouter, Depends, status
from fastapi.testclient import TestClient
from tests.base import BaseRouterTest
from micro_cold_spray.core.base.router import (
    add_health_endpoints,
    create_service_dependency
)


@pytest.mark.unit
class TestBaseRouter(BaseRouterTest):
    """Test base router functionality."""

    def test_router_setup(self, app, router):
        """Test basic router setup."""
        router.add_api_route("/test", lambda: {"status": "ok"}, methods=["GET"])
        client = self.setup_router(app, router)
        self.assert_endpoint_exists(client, "/test", ["GET"])

    def test_router_with_prefix(self, app, router):
        """Test router setup with prefix."""
        router.add_api_route("/test", lambda: {"status": "ok"}, methods=["GET"])
        client = self.setup_router(app, router, prefix="/api")
        self.assert_endpoint_exists(client, "/api/test", ["GET"])

    def test_router_dependencies(self, app, router, mock_service):
        """Test router with dependencies."""
        app.state.service = mock_service

        async def test_endpoint(service=Depends(create_service_dependency(type(mock_service)))):
            return {"service_name": service._service_name}

        router.add_api_route("/test", test_endpoint, methods=["GET"])
        client = self.setup_router(app, router)
        
        response = client.get("/test")
        self.assert_success_response(response, {"service_name": "test_service"})

    def test_health_endpoints(self, app, router, mock_service):
        """Test health endpoint setup."""
        app.state.service = mock_service
        add_health_endpoints(router, mock_service)
        client = self.setup_router(app, router)
        
        self.assert_endpoint_exists(client, "/health", ["GET"])
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_multiple_routers(self, app):
        """Test multiple routers setup."""
        router1 = APIRouter(prefix="/api/v1")
        router2 = APIRouter(prefix="/api/v2")

        router1.add_api_route("/test", lambda: {"version": "v1"}, methods=["GET"])
        router2.add_api_route("/test", lambda: {"version": "v2"}, methods=["GET"])

        app.include_router(router1)
        app.include_router(router2)
        client = TestClient(app)

        self.assert_endpoint_exists(client, "/api/v1/test", ["GET"])
        self.assert_endpoint_exists(client, "/api/v2/test", ["GET"])

        response1 = client.get("/api/v1/test")
        response2 = client.get("/api/v2/test")
        
        self.assert_success_response(response1, {"version": "v1"})
        self.assert_success_response(response2, {"version": "v2"})
