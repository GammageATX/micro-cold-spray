"""Core test utilities."""

from typing import Dict, Any, Optional
from fastapi import HTTPException
from micro_cold_spray.core.errors.exceptions import AppError


def assert_core_response(response: Dict[str, Any], expected_status: str = "ok") -> None:
    """Assert core service response matches expected format.
    
    Args:
        response: Service response dictionary
        expected_status: Expected status string
    """
    assert "status" in response
    assert response["status"] == expected_status
    assert "message" in response


def assert_core_error(
    exc_info: HTTPException,
    expected_code: int,
    expected_message: Optional[str] = None
) -> None:
    """Assert core error response matches expected format.
    
    Args:
        exc_info: HTTPException from pytest.raises
        expected_code: Expected HTTP status code
        expected_message: Expected error message (optional)
    """
    assert exc_info.status_code == expected_code
    if expected_message:
        assert expected_message in str(exc_info.detail)


def assert_validation_result(result: Dict[str, Any], expected_valid: bool = True) -> None:
    """Assert validation result matches expected format.
    
    Args:
        result: Validation result dictionary
        expected_valid: Expected validation status
    """
    assert "is_valid" in result
    assert result["is_valid"] == expected_valid
    if not expected_valid:
        assert "errors" in result
