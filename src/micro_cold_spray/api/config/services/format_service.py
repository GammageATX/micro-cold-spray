"""Configuration format service implementation."""

import json
import yaml
from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base import create_error
from micro_cold_spray.api.config.services.base_config_service import BaseConfigService


class FormatService(BaseConfigService):
    """Configuration format service implementation."""

    def __init__(self):
        """Initialize service."""
        super().__init__(name="format")
        self._formatters = {
            "json": self._format_json,
            "yaml": self._format_yaml
        }

    async def _start(self) -> None:
        """Start implementation."""
        logger.info("Format service started")

    async def _stop(self) -> None:
        """Stop implementation."""
        logger.info("Format service stopped")

    def _format_json(self, data: Dict[str, Any]) -> str:
        """Format data as JSON.
        
        Args:
            data: Data to format
            
        Returns:
            str: Formatted JSON string
            
        Raises:
            HTTPException: If formatting fails
        """
        try:
            return json.dumps(data, indent=2)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Failed to format JSON: {str(e)}"
            )

    def _format_yaml(self, data: Dict[str, Any]) -> str:
        """Format data as YAML.
        
        Args:
            data: Data to format
            
        Returns:
            str: Formatted YAML string
            
        Raises:
            HTTPException: If formatting fails
        """
        try:
            return yaml.dump(data, default_flow_style=False)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Failed to format YAML: {str(e)}"
            )

    def format(self, data: Dict[str, Any], format_type: str = "json") -> str:
        """Format configuration data.
        
        Args:
            data: Configuration data to format
            format_type: Format type (json or yaml)
            
        Returns:
            str: Formatted configuration string
            
        Raises:
            HTTPException: If service not running or formatting fails
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Format service not running"
            )

        formatter = self._formatters.get(format_type.lower())
        if not formatter:
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Unsupported format type: {format_type}"
            )

        return formatter(data)

    def parse(self, content: str, format_type: str = "json") -> Dict[str, Any]:
        """Parse formatted configuration string.
        
        Args:
            content: Formatted configuration string
            format_type: Format type (json or yaml)
            
        Returns:
            Dict[str, Any]: Parsed configuration data
            
        Raises:
            HTTPException: If service not running or parsing fails
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Format service not running"
            )

        try:
            if format_type.lower() == "json":
                return json.loads(content)
            elif format_type.lower() == "yaml":
                return yaml.safe_load(content)
            else:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Unsupported format type: {format_type}"
                )
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Failed to parse {format_type}: {str(e)}"
            )

    async def health(self) -> dict:
        """Get service health status."""
        health = await super().health()
        health.update({
            "supported_formats": list(self._formatters.keys())
        })
        return health
