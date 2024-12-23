"""Process parameter service implementation."""

from typing import Dict, Any, List
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.process.models import ParameterSet


class ParameterService:
    """Process parameter service implementation."""

    def __init__(self, name: str = "parameter"):
        """Initialize parameter service.
        
        Args:
            name: Service name
        """
        self.name = name
        self._parameter_sets: Dict[str, ParameterSet] = {}
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    async def initialize(self) -> None:
        """Initialize service."""
        logger.info(f"Initializing {self.name} service")

    async def start(self) -> None:
        """Start parameter service."""
        try:
            # Initialize parameter sets
            self._parameter_sets = {}
            self._is_running = True
            logger.info(f"{self.name} service started")
        except Exception as e:
            logger.error(f"Failed to start {self.name} service: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to start {self.name} service",
                context={"error": str(e)},
                cause=e
            )

    async def stop(self) -> None:
        """Stop parameter service."""
        try:
            # Clear parameter sets
            self._parameter_sets.clear()
            self._is_running = False
            logger.info(f"{self.name} service stopped")
        except Exception as e:
            logger.error(f"Failed to stop {self.name} service: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to stop {self.name} service",
                context={"error": str(e)},
                cause=e
            )

    async def create_parameter_set(self, parameter_set: ParameterSet) -> None:
        """Create parameter set.
        
        Args:
            parameter_set: Parameter set to create
            
        Raises:
            HTTPException: If creation fails
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )
            
        try:
            # Validate parameter set
            if parameter_set.id in self._parameter_sets:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Parameter set {parameter_set.id} already exists",
                    context={"parameter_set_id": parameter_set.id}
                )
                
            # Store parameter set
            self._parameter_sets[parameter_set.id] = parameter_set
            logger.info(f"Created parameter set: {parameter_set.id}")
            
        except Exception as e:
            logger.error(f"Failed to create parameter set: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to create parameter set",
                context={"error": str(e)},
                cause=e
            )

    async def get_parameter_set(self, parameter_set_id: str) -> ParameterSet:
        """Get parameter set.
        
        Args:
            parameter_set_id: Parameter set ID
            
        Returns:
            Parameter set
            
        Raises:
            HTTPException: If parameter set not found
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )
            
        try:
            if parameter_set_id not in self._parameter_sets:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Parameter set {parameter_set_id} not found",
                    context={"parameter_set_id": parameter_set_id}
                )
                
            return self._parameter_sets[parameter_set_id]
            
        except Exception as e:
            logger.error(f"Failed to get parameter set {parameter_set_id}: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to get parameter set {parameter_set_id}",
                context={
                    "parameter_set_id": parameter_set_id,
                    "error": str(e)
                },
                cause=e
            )

    async def update_parameter_set(self, parameter_set: ParameterSet) -> None:
        """Update parameter set.
        
        Args:
            parameter_set: Parameter set to update
            
        Raises:
            HTTPException: If update fails
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )
            
        try:
            if parameter_set.id not in self._parameter_sets:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Parameter set {parameter_set.id} not found",
                    context={"parameter_set_id": parameter_set.id}
                )
                
            # Update parameter set
            self._parameter_sets[parameter_set.id] = parameter_set
            logger.info(f"Updated parameter set: {parameter_set.id}")
            
        except Exception as e:
            logger.error(f"Failed to update parameter set: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to update parameter set",
                context={"error": str(e)},
                cause=e
            )

    async def delete_parameter_set(self, parameter_set_id: str) -> None:
        """Delete parameter set.
        
        Args:
            parameter_set_id: Parameter set ID to delete
            
        Raises:
            HTTPException: If deletion fails
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )
            
        try:
            if parameter_set_id not in self._parameter_sets:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Parameter set {parameter_set_id} not found",
                    context={"parameter_set_id": parameter_set_id}
                )
                
            # Delete parameter set
            del self._parameter_sets[parameter_set_id]
            logger.info(f"Deleted parameter set: {parameter_set_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete parameter set: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to delete parameter set",
                context={"error": str(e)},
                cause=e
            )

    async def list_parameter_sets(self) -> List[Dict[str, Any]]:
        """List parameter sets.
        
        Returns:
            List of parameter sets
            
        Raises:
            HTTPException: If listing fails
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )
            
        try:
            return [
                {
                    "id": ps.id,
                    "name": ps.name,
                    "description": ps.description,
                    "metadata": ps.metadata
                }
                for ps in self._parameter_sets.values()
            ]
        except Exception as e:
            logger.error(f"Failed to list parameter sets: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to list parameter sets",
                context={"error": str(e)},
                cause=e
            )

    async def health(self) -> dict:
        """Get service health status.
        
        Returns:
            Health check result
        """
        return {
            "status": "ok" if self.is_running else "error",
            "context": {
                "parameter_sets": len(self._parameter_sets)
            }
        }
