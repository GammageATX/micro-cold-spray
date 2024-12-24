"""Parameter service for process execution."""

from datetime import datetime
import time
from typing import Dict, List, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.process.models.process_models import ParameterSet


class ParameterService:
    """Service for managing process parameters."""

    def __init__(self):
        """Initialize parameter service."""
        self._service_name = "parameter"
        self._version = "1.0.0"
        self._start_time = None
        self._is_running = False
        self._parameter_sets: Dict[str, ParameterSet] = {}
        logger.info("ParameterService initialized")

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
            logger.info("Parameter service initialized")
        except Exception as e:
            error_msg = f"Failed to initialize parameter service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"error": str(e)}
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
            logger.info("Parameter service started")

        except Exception as e:
            error_msg = f"Failed to start parameter service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"error": str(e)}
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
            logger.info("Parameter service stopped")

        except Exception as e:
            error_msg = f"Failed to stop parameter service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"error": str(e)}
            )

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Health status dictionary
        """
        return {
            "status": "ok" if self.is_running else "error",
            "service": self._service_name,
            "version": self._version,
            "running": self.is_running,
            "uptime": self.uptime,
            "parameter_set_count": len(self._parameter_sets)
        }

    async def list_parameter_sets(self) -> List[ParameterSet]:
        """List available parameter sets.
        
        Returns:
            List of parameter sets
            
        Raises:
            HTTPException: If listing fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
            return list(self._parameter_sets.values())
        except Exception as e:
            error_msg = "Failed to list parameter sets"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )

    async def get_parameter_set(self, parameter_set_id: str) -> ParameterSet:
        """Get parameter set by ID.
        
        Args:
            parameter_set_id: Parameter set identifier
            
        Returns:
            Parameter set
            
        Raises:
            HTTPException: If parameter set not found or retrieval fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if parameter_set_id not in self._parameter_sets:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Parameter set {parameter_set_id} not found"
                )

            return self._parameter_sets[parameter_set_id]
        except Exception as e:
            error_msg = f"Failed to get parameter set {parameter_set_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )

    async def create_parameter_set(self, parameter_set: ParameterSet) -> None:
        """Create parameter set.
        
        Args:
            parameter_set: Parameter set to create
            
        Raises:
            HTTPException: If parameter set already exists or creation fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if parameter_set.id in self._parameter_sets:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Parameter set {parameter_set.id} already exists"
                )

            self._parameter_sets[parameter_set.id] = parameter_set
            logger.info(f"Created parameter set: {parameter_set.id}")
        except Exception as e:
            error_msg = f"Failed to create parameter set {parameter_set.id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )

    async def update_parameter_set(self, parameter_set: ParameterSet) -> None:
        """Update parameter set.
        
        Args:
            parameter_set: Parameter set to update
            
        Raises:
            HTTPException: If parameter set not found or update fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if parameter_set.id not in self._parameter_sets:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Parameter set {parameter_set.id} not found"
                )

            self._parameter_sets[parameter_set.id] = parameter_set
            logger.info(f"Updated parameter set: {parameter_set.id}")
        except Exception as e:
            error_msg = f"Failed to update parameter set {parameter_set.id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )

    async def delete_parameter_set(self, parameter_set_id: str) -> None:
        """Delete parameter set.
        
        Args:
            parameter_set_id: Parameter set identifier
            
        Raises:
            HTTPException: If parameter set not found or deletion fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if parameter_set_id not in self._parameter_sets:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Parameter set {parameter_set_id} not found"
                )

            del self._parameter_sets[parameter_set_id]
            logger.info(f"Deleted parameter set: {parameter_set_id}")
        except Exception as e:
            error_msg = f"Failed to delete parameter set {parameter_set_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )
