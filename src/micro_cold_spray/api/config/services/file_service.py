"""File service implementation."""

import os
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth


class FileService:
    """File service."""

    def __init__(self, base_path: str):
        """Initialize service.
        
        Args:
            base_path: Base path for file operations
        """
        self._base_path = base_path
        self._is_running = False
        self._start_time = None
        logger.info("File service initialized")

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            logger.info("Initializing file service...")
            
            # Create base directory if it doesn't exist
            os.makedirs(self._base_path, exist_ok=True)
            logger.info(f"Using base path: {self._base_path}")
            
            logger.info("File service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize file service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start service."""
        try:
            logger.info("Starting file service...")
            self._is_running = True
            self._start_time = datetime.now()
            logger.info("File service started")
            
        except Exception as e:
            self._is_running = False
            error_msg = f"Failed to start file service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            logger.info("Stopping file service...")
            self._is_running = False
            logger.info("File service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop file service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    @property
    def uptime(self) -> float:
        """Get service uptime."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    async def health(self) -> ServiceHealth:
        """Get service health status."""
        try:
            # Check if base directory exists and is writable
            base_exists = os.path.exists(self._base_path)
            base_writable = os.access(self._base_path, os.W_OK) if base_exists else False
            
            # Build component status
            components = {
                "base_dir": ComponentHealth(
                    status="ok" if base_exists and base_writable else "error",
                    error=None if base_exists and base_writable else "Base directory not accessible"
                )
            }
            
            # Overall status is error if any component is in error
            overall_status = "error" if any(c.status == "error" for c in components.values()) else "ok"
            
            return ServiceHealth(
                status=overall_status,
                service="file",
                version="1.0.0",  # TODO: Load from config
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
                service="file",
                version="1.0.0",  # TODO: Load from config
                is_running=False,
                uptime=self.uptime,
                error=error_msg,
                components={
                    "base_dir": ComponentHealth(
                        status="error",
                        error=error_msg
                    )
                }
            )
