"""Configuration utilities."""

from micro_cold_spray.api.config.utils.config_singleton import (
    get_config_service,
    set_config_service
)

__all__ = [
    "get_config_service",
    "set_config_service"
]
