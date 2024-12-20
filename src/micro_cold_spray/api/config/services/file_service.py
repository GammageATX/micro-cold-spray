"""Configuration file service implementation."""

import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config.models.config_models import ConfigData


class ConfigFileService(BaseService):
    """Configuration file service implementation."""

    def __init__(self, name: str = "file"):
        """Initialize service.
        
        Args:
            name: Service name
        """
        super().__init__(name=name)
        self._config_dir: Optional[Path] = None

    async def _start(self) -> None:
        """Start implementation."""
        try:
            await self._initialize()
            logger.info("File service started")
        except Exception as e:
            logger.error(f"Failed to start file service: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to start file service",
                context={"error": str(e)},
                cause=e
            )

    async def _stop(self) -> None:
        """Stop implementation."""
        try:
            await self._cleanup()
            logger.info("File service stopped")
        except Exception as e:
            logger.error(f"Failed to stop file service: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to stop file service",
                context={"error": str(e)},
                cause=e
            )

    async def _initialize(self) -> None:
        """Initialize service."""
        config_dir = os.getenv("CONFIG_DIR", "config")
        self._config_dir = Path(config_dir)
        if not self._config_dir.exists():
            self._config_dir.mkdir(parents=True)

    async def _cleanup(self) -> None:
        """Clean up service."""
        self._config_dir = None

    async def _validate_config(self, config: ConfigData) -> None:
        """Validate configuration.
        
        Args:
            config: Configuration data
            
        Raises:
            HTTPException: If validation fails (422)
        """
        if not config:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Config data cannot be None",
                context={"config": None}
            )

    async def save_config(self, config_type: str, config: ConfigData) -> None:
        """Save configuration to file.
        
        Args:
            config_type: Configuration type
            config: Configuration data
            
        Raises:
            HTTPException: If saving fails (400)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )

        try:
            await self._validate_config(config)
            
            config_file = self._config_dir / f"{config_type}.json"
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)
                
            logger.debug(f"Saved config to file: {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Failed to save config",
                context={"error": str(e)},
                cause=e
            )

    async def load_config(self, config_type: str) -> Optional[Dict[str, Any]]:
        """Load configuration from file.
        
        Args:
            config_type: Configuration type
            
        Returns:
            Configuration data if found
            
        Raises:
            HTTPException: If loading fails (500)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )

        try:
            config_file = self._config_dir / f"{config_type}.json"
            if not config_file.exists():
                return None
                
            with open(config_file) as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to load config",
                context={"error": str(e)},
                cause=e
            )

    async def delete_config(self, config_type: str) -> None:
        """Delete configuration file.
        
        Args:
            config_type: Configuration type
            
        Raises:
            HTTPException: If deletion fails (400)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )

        try:
            config_file = self._config_dir / f"{config_type}.json"
            if config_file.exists():
                config_file.unlink()
                logger.debug(f"Deleted config file: {config_file}")
                
        except Exception as e:
            logger.error(f"Failed to delete config: {e}")
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Failed to delete config",
                context={"error": str(e)},
                cause=e
            )

    async def health(self) -> dict:
        """Get service health status.
        
        Returns:
            Health check result
        """
        health = await super().health()
        health["context"].update({
            "config_dir": str(self._config_dir) if self._config_dir else None
        })
        return health
