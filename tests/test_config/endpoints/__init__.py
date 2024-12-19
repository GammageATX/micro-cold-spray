"""Configuration endpoint tests.

This package contains tests for the configuration API endpoints:

- test_config_endpoints.py: Tests for configuration REST API endpoints
"""

from tests.test_config.endpoints.test_config_endpoints import (
    test_get_config_types,
    test_health_check_success,
    test_update_config_with_backup
)

__all__ = [
    'test_get_config_types',
    'test_health_check_success',
    'test_update_config_with_backup'
]
