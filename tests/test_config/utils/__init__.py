"""Configuration utility tests.

This package contains tests for configuration utility functions:

- test_config_singleton.py: Tests for configuration service singleton pattern
"""

from tests.test_config.utils.test_config_singleton import (
    test_get_config_service_first_call,
    test_get_config_service_subsequent_calls,
    test_cleanup_config_service,
    test_thread_safety,
    test_double_check_locking,
    test_cleanup_idempotent,
    test_cleanup_with_lock,
    test_concurrent_initialization,
    test_lock_exception_handling
)

__all__ = [
    'test_get_config_service_first_call',
    'test_get_config_service_subsequent_calls',
    'test_cleanup_config_service',
    'test_thread_safety',
    'test_double_check_locking',
    'test_cleanup_idempotent',
    'test_cleanup_with_lock',
    'test_concurrent_initialization',
    'test_lock_exception_handling'
]