"""Test base error handling utilities."""

from datetime import datetime
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error


def test_create_error_basic():
    """Test creating basic error."""
    error = create_error(
        message="Test error",
        status_code=status.HTTP_400_BAD_REQUEST
    )
    assert error.status_code == status.HTTP_400_BAD_REQUEST
    assert error.detail["message"] == "Test error"
    assert "timestamp" in error.detail
    assert isinstance(datetime.fromisoformat(error.detail["timestamp"]), datetime)
    assert error.detail["context"] == {}


def test_create_error_with_context():
    """Test error with context."""
    context = {
        "service": "test_service",
        "path": "/test",
        "errors": ["validation error"]
    }
    error = create_error(
        message="Test error",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        context=context
    )
    assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert error.detail["context"] == context


def test_create_error_with_cause():
    """Test error with cause."""
    cause = ValueError("Original error")
    error = create_error(
        message="Test error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        cause=cause
    )
    assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert error.__cause__ == cause


def test_create_error_service():
    """Test service error format."""
    error = create_error(
        message="Service error",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        context={"service": "test", "error": "Failed to start"}
    )
    assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert error.detail["context"]["service"] == "test"
    assert error.detail["context"]["error"] == "Failed to start"


def test_create_error_validation():
    """Test validation error format."""
    error = create_error(
        message="Validation error",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        context={
            "service": "test",
            "errors": ["Invalid format"],
            "expected": "string",
            "received": "int"
        }
    )
    assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert error.detail["context"]["service"] == "test"
    assert error.detail["context"]["errors"] == ["Invalid format"]
    assert error.detail["context"]["expected"] == "string"
    assert error.detail["context"]["received"] == "int"


def test_create_error_http():
    """Test HTTP error format."""
    error = create_error(
        message="Not found",
        status_code=status.HTTP_404_NOT_FOUND,
        context={"path": "/test", "service": "test"}
    )
    assert error.status_code == status.HTTP_404_NOT_FOUND
    assert error.detail["context"]["path"] == "/test"
    assert error.detail["context"]["service"] == "test"


def test_create_error_registry():
    """Test registry error format."""
    error = create_error(
        message="Service not found",
        status_code=status.HTTP_404_NOT_FOUND,
        context={"service": "test", "service_type": "TestService"}
    )
    assert error.status_code == status.HTTP_404_NOT_FOUND
    assert error.detail["context"]["service"] == "test"
    assert error.detail["context"]["service_type"] == "TestService"
