"""Tests for base exceptions."""

from micro_cold_spray.api.base.exceptions import (
    APIError,
    OperationError,
    HardwareError
)


class TestExceptions:
    """Test exception functionality."""
    
    def test_api_error(self):
        """Test APIError with context."""
        context = {"detail": "test error"}
        error = APIError("Test message", context)
        assert str(error) == "Test message"
        assert error.context == context
        
    def test_operation_error(self):
        """Test OperationError specifics."""
        error = OperationError(
            message="Failed operation",
            operation_type="test_op",
            context={"detail": "test"}
        )
        assert error.operation_type == "test_op"
        assert "detail" in error.context
        
    def test_hardware_error(self):
        """Test HardwareError specifics."""
        error = HardwareError(
            message="Hardware failure",
            device="test_device",
            context={"detail": "test"}
        )
        assert error.device == "test_device"
        assert "detail" in error.context
