"""Schema service implementation."""

import os
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth


class SchemaService:
    """Schema service."""

    def __init__(self, schema_path: str, version: str = "1.0.0"):
        """Initialize service.
        
        Args:
            schema_path: Path to schema directory
            version: Service version from config
        """
        self._service_name = "schema"
        self._version = version
        self._schema_path = schema_path
        self._is_running = False
        self._start_time = None
        self._schemas = {}
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
            
            # Create schema directory if it doesn't exist
            os.makedirs(self._schema_path, exist_ok=True)
            logger.info(f"Using schema path: {self._schema_path}")
            
            # Load existing schemas
            self._schemas = {}  # TODO: Load schemas from files
            
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
            # Check if schema directory exists and is writable
            path_exists = os.path.exists(self._schema_path)
            path_writable = os.access(self._schema_path, os.W_OK) if path_exists else False
            
            # Build component status
            components = {
                "schema_dir": ComponentHealth(
                    status="ok" if path_exists and path_writable else "error",
                    error=None if path_exists and path_writable else "Schema directory not accessible"
                ),
                "schemas": ComponentHealth(
                    status="ok" if self._schemas else "error",
                    error=None if self._schemas else "No schemas loaded"
                )
            }
            
            # Overall status is error if any component is in error
            overall_status = "error" if any(c.status == "error" for c in components.values()) else "ok"
            
            return ServiceHealth(
                status=overall_status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if overall_status == "ok" else "One or more components in error state",
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
                components={
                    "schema_dir": ComponentHealth(
                        status="error",
                        error=error_msg
                    ),
                    "schemas": ComponentHealth(
                        status="error",
                        error=error_msg
                    )
                }
            )
