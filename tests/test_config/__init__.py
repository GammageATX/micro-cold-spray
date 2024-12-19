"""Configuration test package.

This package contains tests for the configuration service and related components.
Tests are organized into submodules for different aspects of the configuration system:

- endpoints: Tests for API endpoints
- models: Tests for data models
- services: Tests for service components
- utils: Tests for utility functions
"""

from tests.test_config.config_test_base import (
    create_test_app,
    create_test_client,
    test_service_lifecycle
)

__all__ = [
    'create_test_app',
    'create_test_client',
    'test_service_lifecycle'
]
