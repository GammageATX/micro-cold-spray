"""Base test classes for all tests."""

import pytest
from typing import Dict, Any, Optional, Type
from fastapi import status, FastAPI, APIRouter
from fastapi.testclient import TestClient
import httpx
from unittest.mock import MagicMock


class BaseTest:
    """Base class for all tests providing common utilities."""
    
    def setup_method(self):
        """Basic setup for all tests."""
        pass

    def assert_dict_contains(self, actual: Dict[str, Any], expected: Dict[str, Any]):
        """Assert that actual dictionary contains all key-value pairs from expected.
        
        Args:
            actual: Actual dictionary to check
            expected: Expected key-value pairs that should be in actual
        """
        for key, value in expected.items():
            assert key in actual
            if isinstance(value, dict):
                self.assert_dict_contains(actual[key], value)
            else:
                assert actual[key] == value


class BaseAPITest(BaseTest):
    """Base class for API tests with HTTP client utilities."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, test_client: TestClient, async_client: httpx.AsyncClient):
        """Set up test method with API clients.
        
        Args:
            test_client: Synchronous FastAPI test client
            async_client: Asynchronous FastAPI test client
        """
        super().setup_method()
        self.client = test_client
        self.async_client = async_client
        
    def assert_success_response(self, response, expected_data: Optional[Dict[str, Any]] = None):
        """Assert that the response is successful and contains expected data.
        
        Args:
            response: FastAPI response object
            expected_data: Expected response data dictionary
        """
        assert response.status_code == status.HTTP_200_OK
        if expected_data:
            self.assert_dict_contains(response.json(), expected_data)
        
    def assert_error_response(self, response, status_code: int = 400, error_message: Optional[str] = None):
        """Assert that the response is an error with expected status and message.
        
        Args:
            response: FastAPI response object
            status_code: Expected HTTP status code
            error_message: Expected error message
        """
        assert response.status_code == status_code
        if error_message:
            data = response.json()
            assert "detail" in data
            if isinstance(data["detail"], dict):
                assert "message" in data["detail"]
                assert error_message in data["detail"]["message"]
            else:
                assert error_message in data["detail"]

    def assert_health_check(self, response):
        """Assert that a health check response is valid.
        
        Args:
            response: Health check response object
        """
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check required fields
        assert "status" in data
        assert "service_info" in data
        
        # Check service info fields
        service_info = data["service_info"]
        assert "name" in service_info
        assert "version" in service_info
        assert "running" in service_info
        assert "uptime" in service_info
        
        # Validate status
        assert data["status"] in ["ok", "error", "degraded", "stopped"]
        
        # Validate version format
        assert isinstance(service_info["version"], str)
        
        # Validate uptime is a number or None
        assert service_info["uptime"] is None or isinstance(service_info["uptime"], (int, float))
        if service_info["uptime"] is not None:
            assert service_info["uptime"] >= 0

    async def assert_async_success_response(self, response, expected_data: Optional[Dict[str, Any]] = None):
        """Assert that the async response is successful and contains expected data.
        
        Args:
            response: Async FastAPI response object
            expected_data: Expected response data dictionary
        """
        assert response.status_code == status.HTTP_200_OK
        if expected_data:
            data = await response.json()
            self.assert_dict_contains(data, expected_data)
    
    async def assert_async_error_response(self, response, status_code: int = 400, error_message: Optional[str] = None):
        """Assert that the async response is an error with expected status and message.
        
        Args:
            response: Async FastAPI response object
            status_code: Expected HTTP status code
            error_message: Expected error message
        """
        assert response.status_code == status_code
        if error_message:
            data = await response.json()
            assert "detail" in data
            if isinstance(data["detail"], dict):
                assert "message" in data["detail"]
                assert error_message in data["detail"]["message"]
            else:
                assert error_message in data["detail"]


class BaseServiceTest(BaseTest):
    """Base class for service unit tests."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, mock_base_service):
        """Set up test method with mock service.
        
        Args:
            mock_base_service: Mock base service fixture
        """
        super().setup_method()
        self.service = mock_base_service

    def assert_service_running(self):
        """Assert that service is in running state."""
        assert self.service.is_running
        assert self.service.start_time is not None
        assert self.service.uptime is not None
        assert self.service.uptime.total_seconds() >= 0

    def assert_service_stopped(self):
        """Assert that service is in stopped state."""
        assert not self.service.is_running
        assert self.service.start_time is None
        assert self.service.uptime is None


class BaseRouterTest(BaseAPITest):
    """Base class for router unit tests."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test FastAPI application."""
        return FastAPI()

    @pytest.fixture
    def router(self) -> APIRouter:
        """Create test router."""
        return APIRouter()

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        service = MagicMock()
        service.is_running = True
        service.start_time = None
        service._service_name = "test_service"
        service.version = "1.0.0"
        return service

    def setup_router(self, app: FastAPI, router: APIRouter, prefix: str = ""):
        """Set up router with app.
        
        Args:
            app: FastAPI application
            router: Router to set up
            prefix: Optional URL prefix
        """
        if prefix:
            app.include_router(router, prefix=prefix)
        else:
            app.include_router(router)
        return TestClient(app)

    def assert_endpoint_exists(self, client: TestClient, path: str, methods: list[str]):
        """Assert that endpoint exists and supports specified methods.
        
        Args:
            client: Test client
            path: Endpoint path
            methods: List of HTTP methods to check
        """
        for method in methods:
            response = client.request(method, path)
            assert response.status_code != status.HTTP_404_NOT_FOUND


class BaseAppTest(BaseAPITest):
    """Base class for application tests."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test FastAPI application."""
        return FastAPI()

    def assert_middleware_exists(self, app: FastAPI, middleware_class: Type):
        """Assert that middleware exists in application.
        
        Args:
            app: FastAPI application
            middleware_class: Expected middleware class
        """
        middleware_found = False
        for middleware in app.user_middleware:
            if middleware.cls == middleware_class:
                middleware_found = True
                break
        assert middleware_found

    def assert_exception_handler_exists(self, app: FastAPI, exception_type: Type[Exception]):
        """Assert that exception handler exists.
        
        Args:
            app: FastAPI application
            exception_type: Expected exception type
        """
        assert exception_type in app.exception_handlers


class BaseConfigTest(BaseTest):
    """Base class for configuration tests."""

    def assert_config_loaded(self, config, env: str = "test"):
        """Assert that configuration is properly loaded.
        
        Args:
            config: Configuration object
            env: Expected environment name
        """
        assert hasattr(config, "current_env")
        assert config.current_env == env
        assert hasattr(config, "settings")

    def assert_config_value(self, config, key: str, expected_value: Any):
        """Assert configuration value.
        
        Args:
            config: Configuration object
            key: Configuration key
            expected_value: Expected value
        """
        assert hasattr(config, key)
        assert getattr(config, key) == expected_value

    def assert_config_structure(self, config, required_keys: list[str]):
        """Assert that configuration has required structure.
        
        Args:
            config: Configuration object
            required_keys: List of required configuration keys
        """
        for key in required_keys:
            assert hasattr(config, key)


class BaseIntegrationTest(BaseAPITest):
    """Base class for integration tests."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, app, test_client, async_client):
        """Set up test method with app and clients.
        
        Args:
            app: FastAPI application
            test_client: Synchronous FastAPI test client
            async_client: Asynchronous FastAPI test client
        """
        super().setup_method(test_client, async_client)
        self.app = app
