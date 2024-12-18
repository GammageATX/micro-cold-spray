"""Test utilities."""

from typing import Dict, Any, Optional, Union
from fastapi import HTTPException


def assert_error_response(
    exc_info: Union[HTTPException, Any],
    expected_code: int,
    expected_message: Optional[str] = None
):
    """Assert error response matches expected format.
    
    Args:
        exc_info: HTTPException or pytest.raises context
        expected_code: Expected HTTP status code
        expected_message: Expected error message (optional)
    """
    # Handle both direct HTTPException and pytest.raises context
    exc = exc_info.value if hasattr(exc_info, 'value') else exc_info
    
    # Verify status code and message
    assert exc.status_code == expected_code
    if expected_message:
        assert expected_message in str(exc.detail)


def assert_service_response(response: Dict[str, Any], expected_status: str = "ok"):
    """Assert service response matches expected format.
    
    Args:
        response: Service response dictionary
        expected_status: Expected status string
    """
    assert "status" in response
    assert response["status"] == expected_status
    assert "message" in response


def assert_health_response(response: Dict[str, Any], service_name: str):
    """Assert health check response matches expected format.
    
    Args:
        response: Health check response dictionary
        service_name: Expected service name
    """
    assert "status" in response
    assert "service_name" in response
    assert response["service_name"] == service_name
    assert "version" in response
    assert "is_running" in response
