"""Unit tests for base application functionality."""

import pytest
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from tests.base import BaseAppTest
from micro_cold_spray.core.errors.exceptions import ServiceError, ConfigurationError


@pytest.mark.unit
class TestBaseApp(BaseAppTest):
    """Test base application functionality."""

    def test_app_creation(self, app):
        """Test basic app creation."""
        assert isinstance(app, FastAPI)
        assert app.title == "FastAPI"  # Default title

    def test_cors_middleware(self, app):
        """Test CORS middleware setup."""
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.assert_middleware_exists(app, CORSMiddleware)

    def test_custom_middleware(self, app):
        """Test custom middleware setup."""
        async def custom_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Custom"] = "test"
            return response

        app.middleware("http")(custom_middleware)
        client = TestClient(app)
        
        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test")
        assert response.headers["X-Custom"] == "test"

    def test_exception_handlers(self, app):
        """Test exception handlers setup."""
        @app.exception_handler(ServiceError)
        async def service_error_handler(request: Request, exc: ServiceError):
            return JSONResponse(
                status_code=503,
                content={"detail": str(exc)}
            )

        @app.exception_handler(ConfigurationError)
        async def config_error_handler(request: Request, exc: ConfigurationError):
            return JSONResponse(
                status_code=503,
                content={"detail": str(exc)}
            )

        self.assert_exception_handler_exists(app, ServiceError)
        self.assert_exception_handler_exists(app, ConfigurationError)

    def test_app_state(self, app, mock_service):
        """Test application state management."""
        app.state.service = mock_service
        assert hasattr(app.state, "service")
        assert app.state.service == mock_service

    def test_app_startup(self, app, mock_service):
        """Test application startup events."""
        startup_called = False

        @app.on_event("startup")
        async def startup_event():
            nonlocal startup_called
            startup_called = True

        app.state.service = mock_service
        with TestClient(app):
            assert startup_called

    def test_app_shutdown(self, app, mock_service):
        """Test application shutdown events."""
        shutdown_called = False

        @app.on_event("shutdown")
        async def shutdown_event():
            nonlocal shutdown_called
            shutdown_called = True

        app.state.service = mock_service
        with TestClient(app):
            pass
        assert shutdown_called

    def test_app_version(self, app):
        """Test application version."""
        app.version = "1.0.0"
        assert app.version == "1.0.0"

    def test_app_docs(self, app):
        """Test application documentation endpoints."""
        client = TestClient(app)
        self.assert_endpoint_exists(client, "/docs", ["GET"])
        self.assert_endpoint_exists(client, "/redoc", ["GET"])
        self.assert_endpoint_exists(client, "/openapi.json", ["GET"])
