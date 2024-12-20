"""Configuration file service implementation."""

import os
import json
from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base import create_error
from micro_cold_spray.api.config.services.base_config_service import BaseConfigService


class FileService(BaseConfigService):
    """Configuration file service implementation."""

    def __init__(self, base_path: str = None):
        """Initialize service.
        
        Args:
            base_path: Base path for config files
        """
        super().__init__(name="file")
        self.base_path = base_path or os.path.join(os.getcwd(), "config")

    async def _start(self) -> None:
        """Start implementation."""
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)
            logger.info(f"Created config directory: {self.base_path}")

    async def _stop(self) -> None:
        """Stop implementation."""
        pass

    def read(self, filename: str) -> Dict[str, Any]:
        """Read configuration from file.
        
        Args:
            filename: Configuration filename
            
        Returns:
            Dict[str, Any]: Configuration data
            
        Raises:
            HTTPException: If service not running or file error
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="File service not running"
            )

        filepath = os.path.join(self.base_path, filename)
        if not os.path.exists(filepath):
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Configuration file not found: {filename}"
            )

        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid JSON in configuration file: {str(e)}"
            )
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to read configuration file: {str(e)}"
            )

    def write(self, filename: str, data: Dict[str, Any]) -> None:
        """Write configuration to file.
        
        Args:
            filename: Configuration filename
            data: Configuration data to write
            
        Raises:
            HTTPException: If service not running or file error
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="File service not running"
            )

        filepath = os.path.join(self.base_path, filename)
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to write configuration file: {str(e)}"
            )

    def delete(self, filename: str) -> None:
        """Delete configuration file.
        
        Args:
            filename: Configuration filename
            
        Raises:
            HTTPException: If service not running or file error
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="File service not running"
            )

        filepath = os.path.join(self.base_path, filename)
        if not os.path.exists(filepath):
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Configuration file not found: {filename}"
            )

        try:
            os.remove(filepath)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to delete configuration file: {str(e)}"
            )

    def list_configs(self) -> list[str]:
        """List available configuration files.
        
        Returns:
            list[str]: List of configuration filenames
            
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="File service not running"
            )

        try:
            return [f for f in os.listdir(self.base_path) if f.endswith('.json')]
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to list configuration files: {str(e)}"
            )

    async def health(self) -> dict:
        """Get service health status."""
        health = await super().health()
        try:
            config_count = len(self.list_configs()) if self.is_running else 0
            health.update({
                "config_count": config_count,
                "base_path": self.base_path
            })
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to get config count: {e}")
            health.update({
                "config_count": 0,
                "base_path": self.base_path,
                "error": str(e)
            })
        return health
