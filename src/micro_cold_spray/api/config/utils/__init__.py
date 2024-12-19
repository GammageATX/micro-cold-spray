"""Configuration utilities."""

from micro_cold_spray.api.config.utils.config_singleton import (
    get_config_service,
    cleanup_config_service,
    _config_service,
    _lock
)

__all__ = [
    "get_config_service",
    "cleanup_config_service",
    "_config_service",  # Expose for testing
    "_lock"  # Expose for testing
]
