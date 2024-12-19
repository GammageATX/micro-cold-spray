"""Configuration service tests.

This package contains tests for configuration service components:

- test_config_cache_service.py: Tests for configuration caching
- test_config_file_service.py: Tests for file operations
- test_config_format_service.py: Tests for data formatting
- test_config_registry_service.py: Tests for service registry
- test_config_schema_service.py: Tests for schema validation
"""

# Cache Service Tests
from tests.test_config.services.test_config_cache_service import (
    test_service_lifecycle as test_cache_service_lifecycle,
    test_service_start_error as test_cache_service_start_error,
    test_service_stop_error,
    test_cache_entry_validation,
    test_cache_config,
    test_get_cached_config_missing,
    test_get_cached_config_expired,
    test_cache_config_invalid,
    test_cache_config_error
)

# File Service Tests
from tests.test_config.services.test_config_file_service import (
    test_create_backup,
    test_create_backup_with_existing_backup,
    test_exists,
    test_load_config,
    test_load_invalid_config,
    test_save_config,
    test_save_config_with_backup
)

# Format Service Tests
from tests.test_config.services.test_config_format_service import (
    test_service_start as test_format_service_start,
    test_service_start_error as test_format_service_start_error,
    test_singleton,
    test_register_format,
    test_register_format_duplicate,
    test_register_format_error,
    test_validate_format_unknown,
    test_validate_format_error
)

# Registry Service Tests
from tests.test_config.services.test_config_registry_service import (
    test_service_start as test_registry_service_start,
    test_service_start_error as test_registry_service_start_error,
    test_validate_references_valid,
    test_validate_references_invalid,
    test_validate_references_with_tags,
    test_validate_references_with_error
)

# Schema Service Tests
from tests.test_config.services.test_config_schema_service import (
    test_service_start as test_schema_service_start,
    test_service_start_error as test_schema_service_start_error,
    test_load_schemas,
    test_load_schemas_invalid_format,
    test_load_schemas_invalid_json,
    test_get_schema,
    test_build_schema,
    test_build_schema_invalid,
    test_validate_config
)

__all__ = [
    # Cache Service
    'test_cache_service_lifecycle',
    'test_cache_service_start_error',
    'test_service_stop_error',
    'test_cache_entry_validation',
    'test_cache_config',
    'test_get_cached_config_missing',
    'test_get_cached_config_expired',
    'test_cache_config_invalid',
    'test_cache_config_error',
    
    # File Service
    'test_create_backup',
    'test_create_backup_with_existing_backup',
    'test_exists',
    'test_load_config',
    'test_load_invalid_config',
    'test_save_config',
    'test_save_config_with_backup',
    
    # Format Service
    'test_format_service_start',
    'test_format_service_start_error',
    'test_singleton',
    'test_register_format',
    'test_register_format_duplicate',
    'test_register_format_error',
    'test_validate_format_unknown',
    'test_validate_format_error',
    
    # Registry Service
    'test_registry_service_start',
    'test_registry_service_start_error',
    'test_validate_references_valid',
    'test_validate_references_invalid',
    'test_validate_references_with_tags',
    'test_validate_references_with_error',
    
    # Schema Service
    'test_schema_service_start',
    'test_schema_service_start_error',
    'test_load_schemas',
    'test_load_schemas_invalid_format',
    'test_load_schemas_invalid_json',
    'test_get_schema',
    'test_build_schema',
    'test_build_schema_invalid',
    'test_validate_config'
]
