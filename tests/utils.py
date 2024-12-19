"""Common test utilities."""

from typing import Dict, Any, Optional
from fastapi import status
from fastapi.testclient import TestClient

def assert_success_response(response, expected_data: Optional[Dict[str, Any]] = None):
    """Assert that the response is successful and contains expected data.
    
    Args:
        response: FastAPI response object
        expected_data: Expected response data dictionary
    """
    assert response.status_code == status.HTTP_200_OK
    if expected_data:
        assert response.json() == expected_data

def assert_error_response(response, status_code: int = 400, error_message: Optional[str] = None):
    """Assert that the response is an error with expected status and message.
    
    Args:
        response: FastAPI response object
        status_code: Expected HTTP status code
        error_message: Expected error message
    """
    assert response.status_code == status_code
    if error_message:
        assert response.json()["detail"] == error_message

def assert_health_check(response):
    """Assert that a health check response is valid.
    
    Args:
        response: Health check response object
    """
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "uptime" in data
    
    # Validate status
    assert data["status"] in ["ok", "error", "healthy"]
    
    # Validate version format
    assert isinstance(data["version"], str)
    
    # Validate uptime is a positive number
    if data["uptime"] is not None:
        assert isinstance(data["uptime"], (int, float))
        assert data["uptime"] >= 0

def assert_validation_error(response, field: str, message: str):
    """Assert that the response contains a validation error.
    
    Args:
        response: FastAPI response object
        field: Field that failed validation
        message: Expected validation error message
    """
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    errors = response.json()["detail"]
    assert any(
        error["loc"][0] == field and error["msg"] == message
        for error in errors
    ) 