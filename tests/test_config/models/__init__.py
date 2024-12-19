"""Configuration model tests.

This package contains tests for configuration data models:

- test_config_models.py: Tests for configuration data models and validation
"""

from tests.test_config.models.test_config_models import (
    test_config_data_get_simple,
    test_config_data_get_nested,
    test_config_data_get_non_dict_values,
    test_config_data_get_empty_key,
    test_config_data_get_non_dict_data,
    test_config_schema_type_validation,
    test_format_metadata,
    test_config_reference,
    test_config_validation_result,
    test_config_update
)

__all__ = [
    'test_config_data_get_simple',
    'test_config_data_get_nested',
    'test_config_data_get_non_dict_values',
    'test_config_data_get_empty_key',
    'test_config_data_get_non_dict_data',
    'test_config_schema_type_validation',
    'test_format_metadata',
    'test_config_reference',
    'test_config_validation_result',
    'test_config_update'
]
