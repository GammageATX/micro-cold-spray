"""Configuration service singleton utilities."""

import threading
from typing import Optional

from loguru import logger

from micro_cold_spray.api.base.base_registry import get_service
from micro_cold_spray.api.config.config_service import ConfigService

# Global singleton instance
_config_service: Optional[ConfigService] = None
_lock = threading.Lock()


def get_config_service() -> ConfigService:
    """Get config service instance.

    Returns:
        ConfigService: Service instance

    Raises:
        Exception: If service cannot be retrieved
    """
    global _config_service

    if _config_service is None:
        with _lock:
            # Double-check pattern
            if _config_service is None:
                try:
                    _config_service = ConfigService(service_name="config")
                except Exception as e:
                    logger.error(f"Failed to initialize config service: {e}")
                    raise RuntimeError(f"Failed to initialize config service: {e}") from e

    return _config_service


def cleanup_config_service() -> None:
    """Clean up config service singleton instance."""
    global _config_service

    with _lock:
        if _config_service is not None:
            _config_service = None
            logger.info("Cleaned up config service singleton")
