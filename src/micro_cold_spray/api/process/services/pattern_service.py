"""Pattern service for process execution."""

from datetime import datetime
import time
from typing import Dict, List, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils import ServiceHealth, get_uptime
from micro_cold_spray.api.process.models.process_models import ProcessPattern


class PatternService:
    """Service for managing process patterns."""

    def __init__(self):
        """Initialize pattern service."""
        self._service_name = "pattern"
        self._version = "1.0.0"
        self._start_time = None
        self._is_running = False
        self._patterns: Dict[str, ProcessPattern] = {}
        logger.info("PatternService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self._start_time.timestamp() if self._start_time else 0

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            logger.info("Pattern service initialized")
        except Exception as e:
            error_msg = f"Failed to initialize pattern service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                details={"error": str(e)}
            )

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            self._start_time = datetime.now()
            self._is_running = True
            logger.info("Pattern service started")

        except Exception as e:
            error_msg = f"Failed to start pattern service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                details={"error": str(e)}
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service not running"
                )

            self._is_running = False
            self._start_time = None
            logger.info("Pattern service stopped")

        except Exception as e:
            error_msg = f"Failed to stop pattern service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                details={"error": str(e)}
            )

    async def health(self) -> ServiceHealth:
        """Get service health status.
        
        Returns:
            ServiceHealth: Health status
        """
        try:
            return ServiceHealth(
                status="ok" if self.is_running else "error",
                service=self._service_name,
                version=self._version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if self.is_running else "Service not running",
                components={
                    "pattern_store": {
                        "status": "ok" if self.is_running else "error",
                        "error": None if self.is_running else "Pattern store not running"
                    }
                }
            )
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service=self._service_name,
                version=self._version,
                is_running=False,
                uptime=0.0,
                error=error_msg,
                components={
                    "pattern_store": {
                        "status": "error",
                        "error": error_msg
                    }
                }
            )

    async def list_patterns(self) -> List[ProcessPattern]:
        """List available patterns.
        
        Returns:
            List of patterns
            
        Raises:
            HTTPException: If listing fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
            return list(self._patterns.values())
        except Exception as e:
            error_msg = "Failed to list patterns"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                details={"error": str(e)}
            )

    async def get_pattern(self, pattern_id: str) -> ProcessPattern:
        """Get pattern by ID.
        
        Args:
            pattern_id: Pattern identifier
            
        Returns:
            Pattern
            
        Raises:
            HTTPException: If pattern not found or retrieval fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if pattern_id not in self._patterns:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Pattern {pattern_id} not found"
                )

            return self._patterns[pattern_id]
        except Exception as e:
            error_msg = f"Failed to get pattern {pattern_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                details={"error": str(e)}
            )

    async def create_pattern(self, pattern: ProcessPattern) -> None:
        """Create pattern.
        
        Args:
            pattern: Pattern to create
            
        Raises:
            HTTPException: If pattern already exists or creation fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if pattern.id in self._patterns:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Pattern {pattern.id} already exists"
                )

            self._patterns[pattern.id] = pattern
            logger.info(f"Created pattern: {pattern.id}")
        except Exception as e:
            error_msg = f"Failed to create pattern {pattern.id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                details={"error": str(e)}
            )

    async def update_pattern(self, pattern: ProcessPattern) -> None:
        """Update pattern.
        
        Args:
            pattern: Pattern to update
            
        Raises:
            HTTPException: If pattern not found or update fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if pattern.id not in self._patterns:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Pattern {pattern.id} not found"
                )

            self._patterns[pattern.id] = pattern
            logger.info(f"Updated pattern: {pattern.id}")
        except Exception as e:
            error_msg = f"Failed to update pattern {pattern.id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                details={"error": str(e)}
            )

    async def delete_pattern(self, pattern_id: str) -> None:
        """Delete pattern.
        
        Args:
            pattern_id: Pattern identifier
            
        Raises:
            HTTPException: If pattern not found or deletion fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if pattern_id not in self._patterns:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Pattern {pattern_id} not found"
                )

            del self._patterns[pattern_id]
            logger.info(f"Deleted pattern: {pattern_id}")
        except Exception as e:
            error_msg = f"Failed to delete pattern {pattern_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                details={"error": str(e)}
            )
