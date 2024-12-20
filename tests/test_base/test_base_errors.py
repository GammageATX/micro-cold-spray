"""Test base errors module."""

import pytest
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_http_error


def test_create_http_error():
    """Test creating HTTP error."""
    error = create_http_error(
        message="Test error",
        status_code=status.HTTP_400_BAD_REQUEST
    )
    assert error.status_code == status.HTTP_400_BAD_REQUEST
    assert str(error.detail) == "Test error"


def test_error_with_cause():
    """Test error with cause."""
    cause = ValueError("Original error")
    error = create_http_error(
        message="Test error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        cause=cause
    )
    assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert str(error.detail) == "Test error"
    assert error.__cause__ == cause


def test_error_with_context():
    """Test error with context."""
    error = create_http_error(
        message="Test error",
        status_code=status.HTTP_400_BAD_REQUEST,
        context={"field": "value"}
    )
    assert error.status_code == status.HTTP_400_BAD_REQUEST
    assert str(error.detail) == "Test error (field=value)"
    assert "field=value" in str(error.detail)
