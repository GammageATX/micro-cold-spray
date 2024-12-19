"""Configuration service singleton."""

from typing import Optional
from loguru import logger

from micro_cold_spray.api.config.config_service import ConfigService


_config_service: Optional[ConfigService] = None


def get_config_service() -> Optional[ConfigService]:
    """Get configuration service singleton instance.
    
    Returns:
        Optional[ConfigService]: Service instance if initialized
    """
    global _config_service
    return _config_service


def set_config_service(service: ConfigService) -> None:
    """Set configuration service singleton instance.
    
    Args:
        service: Service instance to set
    """
    global _config_service
    
    if _config_service and _config_service.is_running:
        logger.warning("Replacing running config service instance")
        
    _config_service = service
    logger.debug("Config service instance set")
