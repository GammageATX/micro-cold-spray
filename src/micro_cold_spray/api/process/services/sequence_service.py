"""Process sequence service implementation."""

from typing import Dict, Any, List
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.process.models import SequenceMetadata


class SequenceService:
    """Process sequence service implementation."""

    def __init__(self, name: str = "sequence"):
        """Initialize sequence service.
        
        Args:
            name: Service name
        """
        self.name = name
        self._sequences: Dict[str, SequenceMetadata] = {}
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    async def initialize(self) -> None:
        """Initialize service."""
        logger.info(f"Initializing {self.name} service")

    async def start(self) -> None:
        """Start sequence service."""
        try:
            # Initialize sequences
            self._sequences = {}
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
        """Stop sequence service."""
        try:
            # Clear sequences
            self._sequences.clear()
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

    async def create_sequence(self, sequence: SequenceMetadata) -> None:
        """Create sequence.
        
        Args:
            sequence: Sequence to create
            
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
            # Validate sequence
            if sequence.id in self._sequences:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Sequence {sequence.id} already exists",
                    context={"sequence_id": sequence.id}
                )
                
            # Store sequence
            self._sequences[sequence.id] = sequence
            logger.info(f"Created sequence: {sequence.id}")
            
        except Exception as e:
            logger.error(f"Failed to create sequence: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to create sequence",
                context={"error": str(e)},
                cause=e
            )

    async def get_sequence(self, sequence_id: str) -> SequenceMetadata:
        """Get sequence.
        
        Args:
            sequence_id: Sequence ID
            
        Returns:
            Sequence
            
        Raises:
            HTTPException: If sequence not found
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )
            
        try:
            if sequence_id not in self._sequences:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not found",
                    context={"sequence_id": sequence_id}
                )
                
            return self._sequences[sequence_id]
            
        except Exception as e:
            logger.error(f"Failed to get sequence {sequence_id}: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to get sequence {sequence_id}",
                context={
                    "sequence_id": sequence_id,
                    "error": str(e)
                },
                cause=e
            )

    async def update_sequence(self, sequence: SequenceMetadata) -> None:
        """Update sequence.
        
        Args:
            sequence: Sequence to update
            
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
            if sequence.id not in self._sequences:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence.id} not found",
                    context={"sequence_id": sequence.id}
                )
                
            # Update sequence
            self._sequences[sequence.id] = sequence
            logger.info(f"Updated sequence: {sequence.id}")
            
        except Exception as e:
            logger.error(f"Failed to update sequence: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to update sequence",
                context={"error": str(e)},
                cause=e
            )

    async def delete_sequence(self, sequence_id: str) -> None:
        """Delete sequence.
        
        Args:
            sequence_id: Sequence ID to delete
            
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
            if sequence_id not in self._sequences:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not found",
                    context={"sequence_id": sequence_id}
                )
                
            # Delete sequence
            del self._sequences[sequence_id]
            logger.info(f"Deleted sequence: {sequence_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete sequence: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to delete sequence",
                context={"error": str(e)},
                cause=e
            )

    async def list_sequences(self) -> List[Dict[str, Any]]:
        """List sequences.
        
        Returns:
            List of sequences
            
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
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "pattern": s.pattern,
                    "parameters": s.parameters,
                    "metadata": s.metadata
                }
                for s in self._sequences.values()
            ]
        except Exception as e:
            logger.error(f"Failed to list sequences: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to list sequences",
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
                "sequences": len(self._sequences)
            }
        }
