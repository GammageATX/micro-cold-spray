"""Format service implementation."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth


class FormatService:
    """Format service."""

    def __init__(self, enabled_formats: List[str], version: str = "1.0.0"):
        """Initialize service.
        
        Args:
            enabled_formats: List of enabled format types
            version: Service version from config
        """
        self._service_name = "format"
        self._version = version
        self._enabled_formats = enabled_formats
        self._is_running = False
        self._start_time = None
        self._formatters = {}
        logger.info(f"{self._service_name} service initialized")

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    @property
    def uptime(self) -> float:
        """Get service uptime."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            logger.info(f"Initializing {self.service_name} service...")
            
            # Initialize formatters for enabled formats
            self._formatters = {fmt: {} for fmt in self._enabled_formats}
            logger.info(f"Enabled formats: {', '.join(self._enabled_formats)}")
            
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start service."""
        try:
            logger.info(f"Starting {self.service_name} service...")
            self._is_running = True
            self._start_time = datetime.now()
            logger.info(f"{self.service_name} service started")
            
        except Exception as e:
            self._is_running = False
            error_msg = f"Failed to start {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            logger.info(f"Stopping {self.service_name} service...")
            self._is_running = False
            logger.info(f"{self.service_name} service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def health(self) -> ServiceHealth:
        """Get service health status."""
        try:
            # Check if formatters are loaded for each enabled format
            components = {}
            for fmt in self._enabled_formats:
                components[fmt] = ComponentHealth(
                    status="ok" if fmt in self._formatters else "error",
                    error=None if fmt in self._formatters else f"Formatter not loaded for {fmt}"
                )
            
            # Overall status is error if any component is in error
            overall_status = "error" if any(c.status == "error" for c in components.values()) else "ok"
            
            return ServiceHealth(
                status=overall_status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if overall_status == "ok" else "One or more formatters not loaded",
                components=components
            )
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service=self.service_name,
                version=self.version,
                is_running=False,
                uptime=self.uptime,
                error=error_msg,
                components={}
            )
