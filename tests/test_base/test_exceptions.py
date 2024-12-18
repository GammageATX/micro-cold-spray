"""Tests for base exceptions."""

from micro_cold_spray.api.base.exceptions import (
    ServiceError,
    ValidationError,
    ConfigurationError,
    CommunicationError,
    DataCollectionError,
    StateError,
    ProcessError,
    MessageError
)


class TestExceptions:
    """Test exception functionality."""
    
    def test_service_error(self):
        """Test base ServiceError with context."""
        context = {"detail": "test error"}
        error = ServiceError("Test message", context)
        assert str(error) == "Test message"
        assert error.context == context
        assert error.message == "Test message"
        
    def test_validation_error(self):
        """Test ValidationError."""
        context = {"field": "test_field"}
        error = ValidationError("Invalid data", context)
        assert str(error) == "Invalid data"
        assert error.context == context
        
    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Bad config")
        assert str(error) == "Bad config"
        assert error.context == {}
        
    def test_communication_error(self):
        """Test CommunicationError."""
        error = CommunicationError("Connection failed")
        assert str(error) == "Connection failed"
        assert error.context == {}
        
    def test_data_collection_error(self):
        """Test DataCollectionError."""
        error = DataCollectionError("Data error")
        assert str(error) == "Data error"
        assert error.context == {}
        
    def test_state_error(self):
        """Test StateError."""
        error = StateError("Invalid state")
        assert str(error) == "Invalid state"
        assert error.context == {}
        
    def test_process_error(self):
        """Test ProcessError."""
        error = ProcessError("Process failed")
        assert str(error) == "Process failed"
        assert error.context == {}
        
    def test_message_error(self):
        """Test MessageError."""
        error = MessageError("Message failed")
        assert str(error) == "Message failed"
        assert error.context == {}
