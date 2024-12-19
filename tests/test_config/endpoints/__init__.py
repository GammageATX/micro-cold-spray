"""Configuration endpoint tests.

This package contains tests for the configuration API endpoints:

- test_config_endpoints.py: Tests for configuration REST API endpoints
"""

from tests.test_config.endpoints.test_config_endpoints import (
    test_create_app,
    test_get_config_types,
    test_health_check_success,
    test_health_check_error,
    test_health_check_stopped,
    test_get_config_success,
    test_get_config_not_found,
    test_update_config_success,
    test_update_config_validation_error,
    test_clear_cache_success,
    test_clear_cache_error
)

__all__ = [
    'test_create_app',
    'test_get_config_types',
    'test_health_check_success',
    'test_health_check_error',
    'test_health_check_stopped',
    'test_get_config_success',
    'test_get_config_not_found',
    'test_update_config_success',
    'test_update_config_validation_error',
    'test_clear_cache_success',
    'test_clear_cache_error'
]
