"""Tests for config service singleton module."""

import threading
import pytest
from unittest.mock import patch, MagicMock

from micro_cold_spray.api.config import singleton
from micro_cold_spray.api.config.config_service import ConfigService


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton state before each test."""
    singleton.cleanup_config_service()
    yield


def test_get_config_service_first_call():
    """Test getting config service for the first time."""
    # First call should create new instance
    service = singleton.get_config_service()
    assert isinstance(service, ConfigService)
    assert service is singleton._config_service  # Check global instance was set


def test_get_config_service_subsequent_calls():
    """Test getting config service multiple times returns same instance."""
    # Get service multiple times
    service1 = singleton.get_config_service()
    service2 = singleton.get_config_service()
    service3 = singleton.get_config_service()
    
    # All calls should return same instance
    assert service1 is service2
    assert service2 is service3
    assert service1 is singleton._config_service


def test_cleanup_config_service():
    """Test cleaning up config service."""
    # Create service
    service = singleton.get_config_service()
    assert singleton._config_service is not None
    
    # Clean up
    singleton.cleanup_config_service()
    assert singleton._config_service is None
    
    # Getting service again should create new instance
    new_service = singleton.get_config_service()
    assert new_service is not service


def test_thread_safety():
    """Test thread safety of singleton pattern."""
    # Track instances created in each thread
    instances = []
    
    def get_instance():
        instances.append(singleton.get_config_service())
    
    # Create and start multiple threads
    threads = [
        threading.Thread(target=get_instance)
        for _ in range(10)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    # All threads should get same instance
    assert len(set(instances)) == 1
    assert all(instance is instances[0] for instance in instances)


def test_double_check_locking():
    """Test double-check locking pattern."""
    # Mock the lock to track acquisitions
    mock_lock = MagicMock()
    mock_lock.__enter__ = MagicMock()
    mock_lock.__exit__ = MagicMock()
    
    with patch('micro_cold_spray.api.config.singleton._lock', mock_lock):
        # First call should use lock
        service1 = singleton.get_config_service()
        assert mock_lock.__enter__.call_count == 1
        
        # Subsequent calls should not use lock
        service2 = singleton.get_config_service()
        assert mock_lock.__enter__.call_count == 1  # Still 1
        
        assert service1 is service2


def test_cleanup_idempotent():
    """Test cleanup can be called multiple times safely."""
    # Create service
    singleton.get_config_service()
    
    # Multiple cleanups should be safe
    singleton.cleanup_config_service()
    singleton.cleanup_config_service()
    singleton.cleanup_config_service()
    
    assert singleton._config_service is None


def test_cleanup_with_lock():
    """Test cleanup properly uses lock."""
    # Mock the lock to track acquisitions
    mock_lock = MagicMock()
    mock_lock.__enter__ = MagicMock()
    mock_lock.__exit__ = MagicMock()
    
    with patch('micro_cold_spray.api.config.singleton._lock', mock_lock):
        singleton.get_config_service()  # Create service
        singleton.cleanup_config_service()  # Clean up
        
        assert mock_lock.__enter__.call_count == 2  # One for create, one for cleanup


def test_concurrent_initialization():
    """Test concurrent initialization attempts."""
    # Mock ConfigService to track instantiations
    mock_service = MagicMock()
    instantiation_count = 0
    
    def mock_init(*args, **kwargs):
        nonlocal instantiation_count
        instantiation_count += 1
        return mock_service
    
    with patch('micro_cold_spray.api.config.singleton.ConfigService', side_effect=mock_init):
        # Simulate concurrent access
        def get_instance():
            singleton.get_config_service()
        
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
    
    with patch('micro_cold_spray.api.config.singleton.ConfigService', side_effect=mock_error):
        with pytest.raises(RuntimeError) as exc_info:
            singleton.get_config_service()
        assert str(exc_info.value) == "Initialization error"
        
        # Global instance should remain None after error
        assert singleton._config_service is None
        
        # Lock should be released
        assert singleton._lock.acquire(blocking=False)
        singleton._lock.release()
