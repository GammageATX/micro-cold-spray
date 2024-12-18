"""Tests for validation exceptions."""

from micro_cold_spray.api.validation.exceptions import (
    ValidationError,
    ParameterError,
    PatternError,
    SequenceError,
    HardwareError,
    RuleError,
    TagError
)


class TestValidationExceptions:
    """Test validation exception classes."""

    def test_validation_error_init(self):
        """Test ValidationError initialization."""
        message = "Test error"
        context = {"field": "value"}
        error = ValidationError(message, context)
        
        assert str(error) == message
        assert error.message == message
        assert error.context == context

    def test_validation_error_without_context(self):
        """Test ValidationError without context."""
        message = "Test error"
        error = ValidationError(message)
        
        assert str(error) == message
        assert error.message == message
        assert error.context is None

    def test_parameter_error(self):
        """Test ParameterError initialization."""
        message = "Parameter error"
        context = {"param": "speed"}
        error = ParameterError(message, context)
        
        assert isinstance(error, ValidationError)
        assert str(error) == message
        assert error.context == context

    def test_pattern_error(self):
        """Test PatternError initialization."""
        message = "Pattern error"
        context = {"pattern": "zigzag"}
        error = PatternError(message, context)
        
        assert isinstance(error, ValidationError)
        assert str(error) == message
        assert error.context == context

    def test_sequence_error(self):
        """Test SequenceError initialization."""
        message = "Sequence error"
        context = {"step": "start"}
        error = SequenceError(message, context)
        
        assert isinstance(error, ValidationError)
        assert str(error) == message
        assert error.context == context

    def test_hardware_error(self):
        """Test HardwareError initialization."""
        message = "Hardware error"
        context = {"device": "feeder"}
        error = HardwareError(message, context)
        
        assert isinstance(error, ValidationError)
        assert str(error) == message
        assert error.context == context

    def test_rule_error(self):
        """Test RuleError initialization."""
        message = "Rule error"
        context = {"rule": "max_steps"}
        error = RuleError(message, context)
        
        assert isinstance(error, ValidationError)
        assert str(error) == message
        assert error.context == context

    def test_tag_error(self):
        """Test TagError initialization."""
        message = "Tag error"
        context = {"tag": "speed"}
        error = TagError(message, context)
        
        assert isinstance(error, ValidationError)
        assert str(error) == message
        assert error.context == context

    def test_error_inheritance(self):
        """Test error class inheritance."""
        errors = [
            ParameterError("test"),
            PatternError("test"),
            SequenceError("test"),
            HardwareError("test"),
            RuleError("test"),
            TagError("test")
        ]
        
        for error in errors:
            assert isinstance(error, ValidationError)
            assert isinstance(error, Exception)
