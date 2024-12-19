"""Base test class and utilities for API testing."""

import pytest
from typing import Dict, Any
from fastapi.testclient import TestClient
import httpx
from datetime import datetime

class BaseAPITest:
    """Base class for API tests providing common functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, test_client: TestClient, async_client: httpx.AsyncClient):
        """Set up test method with clients.
        
        Args:
            test_client: Synchronous FastAPI test client
            async_client: Asynchronous FastAPI test client
        """
        self.client = test_client
        self.async_client = async_client
    
    def assert_success_response(self, response, expected_data: Dict[str, Any] = None):
        """Assert that the response is successful and contains expected data.
        
        Args:
            response: FastAPI response object
            expected_data: Expected response data dictionary
        """
        assert response.status_code == 200
        if expected_data:
            assert response.json() == expected_data
    
    def assert_error_response(self, response, status_code: int = 400, error_message: str = None):
        """Assert that the response is an error with expected status and message.
        
        Args:
            response: FastAPI response object
            status_code: Expected HTTP status code
            error_message: Expected error message
        """
        assert response.status_code == status_code
        if error_message:
            assert response.json()["detail"] == error_message
    
    def assert_health_check(self, response):
        """Assert that a health check response is valid.
        
        Args:
            response: Health check response object
        """
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "uptime" in data
        
        # Validate status
        assert data["status"] in ["ok", "error"]
        
        # Validate version format
        assert isinstance(data["version"], str)
        
        # Validate uptime is a positive number
        assert isinstance(data["uptime"], (int, float))
        assert data["uptime"] >= 0
    
    async def assert_async_success_response(self, response, expected_data: Dict[str, Any] = None):
        """Assert that the async response is successful and contains expected data.
        
        Args:
            response: Async FastAPI response object
            expected_data: Expected response data dictionary
        """
        assert response.status_code == 200
        if expected_data:
            assert await response.json() == expected_data
    
    async def assert_async_error_response(self, response, status_code: int = 400, error_message: str = None):
        """Assert that the async response is an error with expected status and message.
        
        Args:
            response: Async FastAPI response object
            status_code: Expected HTTP status code
            error_message: Expected error message
        """
        assert response.status_code == status_code
        if error_message:
            data = await response.json()
            assert data["detail"] == error_message 