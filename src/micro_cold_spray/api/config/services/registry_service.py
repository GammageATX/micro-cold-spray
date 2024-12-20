"""Configuration registry service implementation."""

from typing import Dict, Any, Optional
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base import create_error
from micro_cold_spray.api.config.services.base_config_service import BaseConfigService


class RegistryService(BaseConfigService):
    """Configuration registry service implementation."""

    def __init__(self):
        """Initialize service."""
        super().__init__(name="registry")
        self._registry: Dict[str, Dict[str, Any]] = {}

    async def _start(self) -> None:
        """Start implementation."""
        self._registry.clear()
        logger.info("Registry service started")

    async def _stop(self) -> None:
        """Stop implementation."""
        self._registry.clear()
        logger.info("Registry service stopped")

    def register(self, name: str, config: Dict[str, Any]) -> None:
        """Register configuration.
        
        Args:
            name: Configuration name
            config: Configuration data
            
        Raises:
            HTTPException: If service not running or config already exists
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Registry service not running"
            )

        if name in self._registry:
            raise create_error(
                status_code=status.HTTP_409_CONFLICT,
                message=f"Configuration already exists: {name}"
            )

        self._registry[name] = config.copy()
        logger.info(f"Registered configuration: {name}")

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get registered configuration.
        
        Args:
            name: Configuration name
            
        Returns:
            Optional[Dict[str, Any]]: Configuration if found
            
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Registry service not running"
            )

        config = self._registry.get(name)
        if not config:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Configuration not found: {name}"
            )

        return config.copy()

    def update(self, name: str, config: Dict[str, Any]) -> None:
        """Update registered configuration.
        
        Args:
            name: Configuration name
            config: New configuration data
            
        Raises:
            HTTPException: If service not running or config not found
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Registry service not running"
            )

        if name not in self._registry:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Configuration not found: {name}"
            )

        self._registry[name] = config.copy()
        logger.info(f"Updated configuration: {name}")

    def delete(self, name: str) -> None:
        """Delete registered configuration.
        
        Args:
            name: Configuration name
            
        Raises:
            HTTPException: If service not running or config not found
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Registry service not running"
            )

        if name not in self._registry:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Configuration not found: {name}"
            )

        del self._registry[name]
        logger.info(f"Deleted configuration: {name}")

    def list_configs(self) -> list[str]:
        """List registered configurations.
        
        Returns:
            list[str]: List of configuration names
            
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Registry service not running"
            )

        return list(self._registry.keys())

    async def health(self) -> dict:
        """Get service health status."""
        health = await super().health()
        health.update({
            "config_count": len(self._registry),
            "configs": list(self._registry.keys())
        })
        return health
