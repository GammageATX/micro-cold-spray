"""Tests for base error handling."""

from micro_cold_spray.api.base.base_errors import (
    AppErrorCode,
    BaseError,
    ServiceError,
    ConfigError,
    ValidationError,
    format_error
)


def test_base_error():
    """Test base error class."""
    error = BaseError(
        message="Test error",
        error_code=AppErrorCode.SERVICE_ERROR,
        context={"detail": "Additional info"}
    )
    assert str(error) == "Test error"
    assert error.error_code == AppErrorCode.SERVICE_ERROR
    assert error.context == {"detail": "Additional info"}


def test_service_error():
    """Test service error class."""
    error = ServiceError("Service error")
    assert str(error) == "Service error"
    assert error.error_code == AppErrorCode.SERVICE_ERROR
    assert error.context == {}

    error_with_context = ServiceError("Service error", context={"service": "test"})
    assert str(error_with_context) == "Service error"
    assert error_with_context.error_code == AppErrorCode.SERVICE_ERROR
    assert error_with_context.context == {"service": "test"}


def test_config_error():
    """Test config error class."""
    error = ConfigError("Config error", {"config": "test"})
    assert str(error) == "Config error"
    assert error.error_code == AppErrorCode.CONFIG_ERROR
    assert error.context == {"config": "test"}


def test_validation_error():
    """Test validation error class."""
    error = ValidationError("Validation error", {"field": "test"})
    assert str(error) == "Validation error"
    assert error.error_code == AppErrorCode.VALIDATION_ERROR
    assert error.context == {"field": "test"}


def test_format_error_basic():
    """Test basic error formatting."""
    error = format_error(AppErrorCode.SERVICE_ERROR, "Test error")
    assert error["error"]["code"] == AppErrorCode.SERVICE_ERROR
    assert error["error"]["message"] == "Test error"
    assert error["error"]["context"] == {}


def test_format_error_with_context():
    """Test error formatting with context."""
    context = {"detail": "Additional info"}
    error = format_error(AppErrorCode.SERVICE_ERROR, "Test error", context)
    assert error["error"]["code"] == AppErrorCode.SERVICE_ERROR
    assert error["error"]["message"] == "Test error"
    assert error["error"]["context"] == context


def test_error_codes():
    """Test error code values."""
    # Service errors
    assert AppErrorCode.SERVICE_ERROR == "SERVICE_ERROR"
    assert AppErrorCode.SERVICE_NOT_FOUND == "SERVICE_NOT_FOUND"
    assert AppErrorCode.SERVICE_NOT_RUNNING == "SERVICE_NOT_RUNNING"
    assert AppErrorCode.SERVICE_ALREADY_RUNNING == "SERVICE_ALREADY_RUNNING"
    
    # Configuration errors
    assert AppErrorCode.CONFIG_ERROR == "CONFIG_ERROR"
    assert AppErrorCode.CONFIG_NOT_FOUND == "CONFIG_NOT_FOUND"
    assert AppErrorCode.CONFIG_INVALID == "CONFIG_INVALID"
    
    # Validation errors
    assert AppErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
    
    # Runtime errors
    assert AppErrorCode.RUNTIME_ERROR == "RUNTIME_ERROR"
    assert AppErrorCode.NOT_IMPLEMENTED == "NOT_IMPLEMENTED"


def test_error_inheritance():
    """Test error class inheritance."""
    assert issubclass(ServiceError, BaseError)
    assert issubclass(ConfigError, BaseError)
    assert issubclass(ValidationError, BaseError)


def test_error_str_representation():
    """Test error string representation."""
    error = BaseError(
        message="Test error",
        error_code=AppErrorCode.SERVICE_ERROR
    )
    assert str(error) == "Test error"
    assert repr(error) == "BaseError('Test error')"
