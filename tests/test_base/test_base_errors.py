"""Test base error handling utilities."""

from datetime import datetime
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error, ConfigError


def test_create_http_error():
    """Test creating HTTP error."""
    error = create_error("Test error")
    assert error.status_code == status.HTTP_400_BAD_REQUEST
    assert error.detail["message"] == "Test error"
    assert "timestamp" in error.detail
    assert "context" in error.detail


def test_error_with_cause():
    """Test error with cause."""
    cause = ValueError("Original error")
    error = create_error("Test error", cause=cause)
    assert error.__cause__ == cause


def test_error_with_context():
    """Test error with context."""
    context = {"key": "value"}
    error = create_error("Test error", context=context)
    assert error.detail["context"] == context


def test_config_error():
    """Test config error."""
    error = ConfigError("Config error")
    assert error.status_code == status.HTTP_400_BAD_REQUEST
    assert error.detail["message"] == "Config error"
    assert "timestamp" in error.detail
    assert "context" in error.detail


def test_config_error_with_context():
    """Test config error with context."""
    context = {"key": "value"}
    error = ConfigError("Config error", context=context)
    assert error.detail["context"] == context


def test_config_error_with_cause():
    """Test config error with cause."""
    cause = ValueError("Original error")
    error = ConfigError("Config error", cause=cause)
    assert error.__cause__ == cause
