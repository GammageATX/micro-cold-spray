"""Configuration service singleton."""

import threading
from typing import Optional
from loguru import logger

from micro_cold_spray.api.config.config_service import ConfigService


_config_service: Optional[ConfigService] = None
_lock = threading.Lock()


def get_config_service() -> ConfigService:
    """Get configuration service singleton instance.
    
    Returns:
        ConfigService: Service instance
    """
    global _config_service
    
    # Double-check locking pattern
    if _config_service is None:
        with _lock:
            if _config_service is None:
                _config_service = ConfigService()
                logger.debug("Created new config service instance")
    
    return _config_service


def cleanup_config_service() -> None:
    """Clean up configuration service singleton instance."""
    global _config_service
    
    with _lock:
        if _config_service is not None:
            if _config_service.is_running:
                logger.warning("Cleaning up running config service instance")
            _config_service = None
            logger.debug("Config service instance cleaned up")


# Expose for testing
_lock = threading.Lock()
