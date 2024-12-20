"""Process pattern service implementation."""

from typing import Dict, Any, List
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.process.models import ProcessPattern


class PatternService(BaseService):
    """Process pattern service implementation."""

    def __init__(self, name: str = "pattern"):
        """Initialize pattern service.
        
        Args:
            name: Service name
        """
        super().__init__(name=name)
        self._patterns: Dict[str, ProcessPattern] = {}

    async def _start(self) -> None:
        """Start pattern service."""
        try:
            # Initialize patterns
            self._patterns = {}
            logger.info("Pattern service started")
        except Exception as e:
            logger.error(f"Failed to start pattern service: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to start pattern service",
                context={"error": str(e)},
                cause=e
            )

    async def _stop(self) -> None:
        """Stop pattern service."""
        try:
            # Clear patterns
            self._patterns.clear()
            logger.info("Pattern service stopped")
        except Exception as e:
            logger.error(f"Failed to stop pattern service: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to stop pattern service",
                context={"error": str(e)},
                cause=e
            )

    async def create_pattern(self, pattern: ProcessPattern) -> None:
        """Create pattern.
        
        Args:
            pattern: Pattern to create
            
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
            # Validate pattern
            if pattern.id in self._patterns:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Pattern {pattern.id} already exists",
                    context={"pattern_id": pattern.id}
                )
                
            # Store pattern
            self._patterns[pattern.id] = pattern
            logger.info(f"Created pattern: {pattern.id}")
            
        except Exception as e:
            logger.error(f"Failed to create pattern: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to create pattern",
                context={"error": str(e)},
                cause=e
            )

    async def get_pattern(self, pattern_id: str) -> ProcessPattern:
        """Get pattern.
        
        Args:
            pattern_id: Pattern ID
            
        Returns:
            Pattern
            
        Raises:
            HTTPException: If pattern not found
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )
            
        try:
            if pattern_id not in self._patterns:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Pattern {pattern_id} not found",
                    context={"pattern_id": pattern_id}
                )
                
            return self._patterns[pattern_id]
            
        except Exception as e:
            logger.error(f"Failed to get pattern {pattern_id}: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to get pattern {pattern_id}",
                context={
                    "pattern_id": pattern_id,
                    "error": str(e)
                },
                cause=e
            )

    async def update_pattern(self, pattern: ProcessPattern) -> None:
        """Update pattern.
        
        Args:
            pattern: Pattern to update
            
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
            if pattern.id not in self._patterns:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Pattern {pattern.id} not found",
                    context={"pattern_id": pattern.id}
                )
                
            # Update pattern
            self._patterns[pattern.id] = pattern
            logger.info(f"Updated pattern: {pattern.id}")
            
        except Exception as e:
            logger.error(f"Failed to update pattern: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to update pattern",
                context={"error": str(e)},
                cause=e
            )

    async def delete_pattern(self, pattern_id: str) -> None:
        """Delete pattern.
        
        Args:
            pattern_id: Pattern ID to delete
            
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
            if pattern_id not in self._patterns:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Pattern {pattern_id} not found",
                    context={"pattern_id": pattern_id}
                )
                
            # Delete pattern
            del self._patterns[pattern_id]
            logger.info(f"Deleted pattern: {pattern_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete pattern: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to delete pattern",
                context={"error": str(e)},
                cause=e
            )

    async def list_patterns(self) -> List[Dict[str, Any]]:
        """List patterns.
        
        Returns:
            List of patterns
            
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
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "metadata": p.metadata
                }
                for p in self._patterns.values()
            ]
        except Exception as e:
            logger.error(f"Failed to list patterns: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to list patterns",
                context={"error": str(e)},
                cause=e
            )

    async def health(self) -> dict:
        """Get service health status.
        
        Returns:
            Health check result
        """
        health = await super().health()
        health["context"].update({
            "patterns": len(self._patterns)
        })
        return health
