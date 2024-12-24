"""Configuration format service implementation."""

import json
import yaml
from typing import Dict, Any
from datetime import datetime
from loguru import logger

from micro_cold_spray.utils.errors import create_error


class FormatService:
    """Configuration format service implementation."""

    def __init__(self):
        """Initialize service."""
        self.is_running = False
        self._start_time = None
        self.formatters = {
            "json": {
                "parse": self._parse_json,
                "format": self._format_json
            },
            "yaml": {
                "parse": self._parse_yaml,
                "format": self._format_yaml
            }
        }

    async def start(self) -> None:
        """Start service."""
        self.is_running = True
        self._start_time = datetime.now()
        logger.info("Format service started")

    async def stop(self) -> None:
        """Stop service."""
        self.is_running = False
        self._start_time = None
        logger.info("Format service stopped")

    def _parse_json(self, data: str) -> Dict[str, Any]:
        """Parse JSON string.
        
        Args:
            data: JSON string to parse
            
        Returns:
            Dict[str, Any]: Parsed data
        """
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise create_error(
                status_code=400,
                message=f"Invalid JSON: {str(e)}"
            )

    def _format_json(self, data: Dict[str, Any]) -> str:
        """Format data as JSON.
        
        Args:
            data: Data to format
            
        Returns:
            str: Formatted JSON string
        """
        try:
            return json.dumps(data, indent=2)
        except Exception as e:
            raise create_error(
                status_code=500,
                message=f"Failed to format JSON: {str(e)}"
            )

    def _parse_yaml(self, data: str) -> Dict[str, Any]:
        """Parse YAML string.
        
        Args:
            data: YAML string to parse
            
        Returns:
            Dict[str, Any]: Parsed data
        """
        try:
            return yaml.safe_load(data)
        except yaml.YAMLError as e:
            raise create_error(
                status_code=400,
                message=f"Invalid YAML: {str(e)}"
            )

    def _format_yaml(self, data: Dict[str, Any]) -> str:
        """Format data as YAML.
        
        Args:
            data: Data to format
            
        Returns:
            str: Formatted YAML string
        """
        try:
            return yaml.dump(data, default_flow_style=False)
        except Exception as e:
            raise create_error(
                status_code=500,
                message=f"Failed to format YAML: {str(e)}"
            )

    def parse(self, data: str, format_type: str) -> Dict[str, Any]:
        """Parse formatted string.
        
        Args:
            data: String to parse
            format_type: Format type ("json" or "yaml")
            
        Returns:
            Dict[str, Any]: Parsed data
        """
        if not self.is_running:
            raise create_error(
                status_code=503,
                message="Format service not running"
            )
        
        if format_type not in self.formatters:
            raise create_error(
                status_code=400,
                message=f"Unsupported format: {format_type}"
            )
        
        return self.formatters[format_type]["parse"](data)

    def format(self, data: Dict[str, Any], format_type: str) -> str:
        """Format data as string.
        
        Args:
            data: Data to format
            format_type: Format type ("json" or "yaml")
            
        Returns:
            str: Formatted string
        """
        if not self.is_running:
            raise create_error(
                status_code=503,
                message="Format service not running"
            )
        
        if format_type not in self.formatters:
            raise create_error(
                status_code=400,
                message=f"Unsupported format: {format_type}"
            )
        
        return self.formatters[format_type]["format"](data)

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Dict[str, Any]: Health status
        """
        return {
            "status": "ok" if self.is_running else "error",
            "is_running": self.is_running,
            "uptime": (datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
            "details": {
                "supported_formats": list(self.formatters.keys())
            }
        }
