"""Tests for base exceptions."""

from micro_cold_spray.api.base.base_exceptions import (
    ServiceError,
    ConfigError,
    ValidationError,
    CommunicationError,
    ProcessError,
    DataError
)


def test_service_error():
    """Test service error."""
    error = ServiceError("Test error")
    assert str(error) == "Test error"
    assert error.context is None


def test_service_error_with_context():
    """Test service error with context."""
    context = {"detail": "Additional info"}
    error = ServiceError("Test error", context)
    assert str(error) == "Test error"
    assert error.context == context


def test_config_error():
    """Test config error."""
    error = ConfigError("Config error")
    assert isinstance(error, ServiceError)
    assert str(error) == "Config error"


def test_validation_error():
    """Test validation error."""
    error = ValidationError("Validation error")
    assert isinstance(error, ServiceError)
    assert str(error) == "Validation error"


def test_communication_error():
    """Test communication error."""
    error = CommunicationError("Communication error")
    assert isinstance(error, ServiceError)
    assert str(error) == "Communication error"


def test_process_error():
    """Test process error."""
    error = ProcessError("Process error")
    assert isinstance(error, ServiceError)
    assert str(error) == "Process error"


def test_data_error():
    """Test data error."""
    error = DataError("Data error")
    assert isinstance(error, ServiceError)
    assert str(error) == "Data error"
