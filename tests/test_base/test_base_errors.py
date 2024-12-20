"""Test base errors module."""

import pytest
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error


@pytest.mark.asyncio
async def test_create_http_error():
    """Test creating HTTP error."""
    error = create_error(
        message="Test error",
        status_code=status.HTTP_400_BAD_REQUEST
    )
    assert error.status_code == status.HTTP_400_BAD_REQUEST
    assert error.detail["message"] == "Test error"
    assert "timestamp" in error.detail


@pytest.mark.asyncio
async def test_error_with_cause():
    """Test error with cause."""
    cause = ValueError("Original error")
    error = create_error(
        message="Test error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        cause=cause
    )
    assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert error.detail["message"] == "Test error"
    assert error.__cause__ == cause
    assert "timestamp" in error.detail


@pytest.mark.asyncio
async def test_error_with_context(mock_datetime):
    """Test error with context."""
    expected_time = mock_datetime.now()
    error = create_error(
        message="Test error",
        status_code=status.HTTP_400_BAD_REQUEST,
        context={"field": "value"}
    )
    assert error.status_code == status.HTTP_400_BAD_REQUEST
    assert error.detail["message"] == "Test error"
    assert error.detail["context"]["field"] == "value"
    assert error.detail["timestamp"][:23] == expected_time.isoformat()[:23]
