"""Unit tests for error handling functionality."""

import pytest
from fastapi import status

from micro_cold_spray.core.errors.codes import AppErrorCode
from micro_cold_spray.core.errors.formatting import (
    format_error,
    format_service_error,
    raise_http_error
)
from micro_cold_spray.core.errors.exceptions import ServiceError

class TestAppErrorCode:
    """Test AppErrorCode functionality."""
    
    @pytest.mark.parametrize("error_code,expected_status", [
        (AppErrorCode.VALIDATION_ERROR, status.HTTP_422_UNPROCESSABLE_ENTITY),
        (AppErrorCode.INVALID_REQUEST, status.HTTP_400_BAD_REQUEST),
        (AppErrorCode.RESOURCE_CONFLICT, status.HTTP_409_CONFLICT),
        (AppErrorCode.RESOURCE_NOT_FOUND, status.HTTP_404_NOT_FOUND),
        (AppErrorCode.SERVICE_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR),
        (AppErrorCode.SERVICE_UNAVAILABLE, status.HTTP_503_SERVICE_UNAVAILABLE),
    ])
    def test_get_status_code(self, error_code, expected_status):
        """Test getting HTTP status code from error code."""
        assert error_code.get_status_code() == expected_status
        
    def test_error_code_values(self):
        """Test error code string values."""
        assert AppErrorCode.VALIDATION_ERROR == "Validation Error"
        assert AppErrorCode.INVALID_REQUEST == "Invalid Request"
        assert AppErrorCode.RESOURCE_CONFLICT == "Resource Conflict"
        assert AppErrorCode.RESOURCE_NOT_FOUND == "Resource Not Found"
        assert AppErrorCode.SERVICE_ERROR == "Service Error"
        assert AppErrorCode.SERVICE_UNAVAILABLE == "Service Unavailable"

class TestErrorFormatting:
    """Test error formatting functionality."""
    
    def test_basic_error(self):
        """Test basic error formatting."""
        error = format_error(
            AppErrorCode.VALIDATION_ERROR,
            "Invalid input"
        )
        assert error == {
            "detail": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input"
            }
        }
        
    def test_error_with_context(self):
        """Test error formatting with context."""
        error = format_error(
            AppErrorCode.RESOURCE_NOT_FOUND,
            "Resource not found",
            {"resource_id": "123", "resource_type": "user"}
        )
        assert error == {
            "detail": {
                "code": "RESOURCE_NOT_FOUND",
                "message": "Resource not found",
                "resource_id": "123",
                "resource_type": "user"
            }
        }
        
    def test_service_error(self):
        """Test service error formatting."""
        error = format_error(
            AppErrorCode.SERVICE_ERROR,
            "Internal server error",
            {"service": "database", "error_code": "DB001"}
        )
        assert error == {
            "detail": {
                "code": "SERVICE_ERROR",
                "message": "Internal server error",
                "service": "database",
                "error_code": "DB001"
            }
        }

    def test_service_error_formatting(self):
        """Test formatting ServiceError instances."""
        error = ServiceError(
            "Service failed",
            {"component": "database", "reason": "connection timeout"}
        )
        formatted = format_service_error(error)
        assert formatted == {
            "detail": {
                "code": "SERVICE_ERROR",
                "message": "Service failed",
                "component": "database",
                "reason": "connection timeout"
            }
        }

    def test_http_error_raising(self):
        """Test raising HTTP errors."""
        with pytest.raises(Exception) as exc_info:
            raise_http_error(
                AppErrorCode.RESOURCE_NOT_FOUND,
                "User not found",
                {"user_id": "123"}
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == {
            "code": "RESOURCE_NOT_FOUND",
            "message": "User not found",
            "user_id": "123"
        } 