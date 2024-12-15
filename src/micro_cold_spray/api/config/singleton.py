"""Config service singleton module.

This module provides a process-local singleton instance of the ConfigService.
Note that each FastAPI application process will get its own instance since they run in separate processes.
"""

from typing import Optional
import threading
from loguru import logger

from .service import ConfigService

_config_service: Optional[ConfigService] = None
_lock = threading.Lock()


def get_config_service() -> ConfigService:
    """Get or create the shared config service instance for this process.
    
    Returns:
        ConfigService: The shared config service instance
        
    Note:
        Each FastAPI application process will get its own instance since they run in separate processes.
        This singleton pattern ensures only one instance exists within each process.
    """
    global _config_service
    
    # Fast path - return existing instance if available
    if _config_service is not None:
        return _config_service
        
    # Slow path - create new instance with lock
    with _lock:
        # Double check pattern in case another thread created instance
        if _config_service is None:
            logger.info("Creating shared config service instance for process {}", id(threading.current_thread()))
            _config_service = ConfigService()
            
    return _config_service


def cleanup_config_service() -> None:
    """Clean up the config service singleton instance.
    
    This should be called during process shutdown to ensure proper cleanup.
    """
    global _config_service
    
    with _lock:
        if _config_service is not None:
            logger.info("Cleaning up shared config service instance")
            _config_service = None
