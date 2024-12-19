"""Test configuration singleton utilities."""

import threading
import pytest
from unittest.mock import MagicMock, patch

from micro_cold_spray.api.config.utils import config_singleton


def test_get_config_service_first_call():
    """Test getting config service for the first time."""
    # First call should create new instance
    service = config_singleton.get_config_service()
    assert service is not None
    assert isinstance(service, config_singleton.ConfigService)


def test_get_config_service_subsequent_calls():
    """Test getting config service multiple times returns same instance."""
    # Get service multiple times
    service1 = config_singleton.get_config_service()
    service2 = config_singleton.get_config_service()
    
    # Should be same instance
    assert service1 is service2


def test_cleanup_config_service():
    """Test cleaning up config service."""
    # Create service
    service = config_singleton.get_config_service()
    assert config_singleton._config_service is not None
    
    # Clean up
    config_singleton.cleanup_config_service()
    assert config_singleton._config_service is None
    
    # Getting service again should create new instance
    new_service = config_singleton.get_config_service()
    assert new_service is not service


def test_thread_safety():
    """Test thread safety of singleton pattern."""
    # Track instances and errors
    instances = []
    errors = []
    
    def get_instance():
        try:
            instances.append(config_singleton.get_config_service())
        except Exception as e:
            errors.append(e)
    
    # Create and start multiple threads
    threads = [threading.Thread(target=get_instance) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    # Check for errors
    assert not errors, f"Errors occurred: {errors}"
    
    # Verify all instances are the same
    first_instance = instances[0]
    for instance in instances[1:]:
        assert instance is first_instance


def test_double_check_locking():
    """Test double-check locking pattern."""
    # Mock the lock to track acquisitions
    mock_lock = MagicMock()
    mock_lock.__enter__ = MagicMock()
    mock_lock.__exit__ = MagicMock()
    
    with patch('micro_cold_spray.api.config.utils.config_singleton._lock', mock_lock):
        # First call should use lock
        service1 = config_singleton.get_config_service()
        assert mock_lock.__enter__.call_count == 1
        assert service1 is not None
        
        # Subsequent calls should not use lock
        service2 = config_singleton.get_config_service()
        assert mock_lock.__enter__.call_count == 1  # Still 1
        assert service2 is service1  # Should be same instance


def test_cleanup_idempotent():
    """Test cleanup can be called multiple times safely."""
    # Create service
    config_singleton.get_config_service()
    
    # Clean up multiple times
    config_singleton.cleanup_config_service()
    config_singleton.cleanup_config_service()  # Should not raise error
    
    assert config_singleton._config_service is None


def test_concurrent_initialization():
    """Test concurrent initialization attempts."""
    # Mock ConfigService to track instantiations
    mock_service = MagicMock()
    instantiation_count = 0
    
    def mock_init(*args, **kwargs):
        nonlocal instantiation_count
        instantiation_count += 1
        return mock_service
    
    with patch('micro_cold_spray.api.config.utils.config_singleton.ConfigService', side_effect=mock_init):
        # Simulate concurrent access
        def get_instance():
            config_singleton.get_config_service()
        
        threads = [threading.Thread(target=get_instance) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should only create one instance despite concurrent attempts
        assert instantiation_count == 1


def test_lock_exception_handling():
    """Test handling of exceptions during locked initialization."""
    # Mock ConfigService to raise an error
    mock_error = RuntimeError("Initialization error")
    
    with patch('micro_cold_spray.api.config.utils.config_singleton.ConfigService', side_effect=mock_error):
        with pytest.raises(RuntimeError) as exc_info:
            config_singleton.get_config_service()
        assert str(exc_info.value) == "Failed to initialize config service: Initialization error"
