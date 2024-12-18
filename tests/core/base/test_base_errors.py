"""Tests for error handling utilities."""

import pytest
from fastapi import status

from micro_cold_spray.api.base.errors import AppErrorCode, format_error


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


class TestFormatError:
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
        
    def test_validation_error(self):
        """Test validation error formatting."""
        error = format_error(
            AppErrorCode.VALIDATION_ERROR,
            "Validation failed",
            {
                "field": "email",
                "value": "invalid",
                "constraint": "email_format"
            }
        )
        assert error == {
            "detail": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "field": "email",
                "value": "invalid",
                "constraint": "email_format"
            }
        }
        
    def test_error_without_context(self):
        """Test error formatting without context."""
        error = format_error(
            AppErrorCode.SERVICE_UNAVAILABLE,
            "Service is down for maintenance"
        )
        assert error == {
            "detail": {
                "code": "SERVICE_UNAVAILABLE",
                "message": "Service is down for maintenance"
            }
        }
        
    def test_error_with_empty_context(self):
        """Test error formatting with empty context."""
        error = format_error(
            AppErrorCode.INVALID_REQUEST,
            "Bad request",
            {}
        )
        assert error == {
            "detail": {
                "code": "INVALID_REQUEST",
                "message": "Bad request"
            }
        }
        
    def test_error_with_nested_context(self):
        """Test error formatting with nested context."""
        error = format_error(
            AppErrorCode.SERVICE_ERROR,
            "Processing failed",
            {
                "request": {
                    "id": "req123",
                    "params": {
                        "action": "process",
                        "data": [1, 2, 3]
                    }
                },
                "error": {
                    "type": "ProcessingError",
                    "details": "Invalid data format"
                }
            }
        )
        assert error == {
            "detail": {
                "code": "SERVICE_ERROR",
                "message": "Processing failed",
                "request": {
                    "id": "req123",
                    "params": {
                        "action": "process",
                        "data": [1, 2, 3]
                    }
                },
                "error": {
                    "type": "ProcessingError",
                    "details": "Invalid data format"
                }
            }
        }
