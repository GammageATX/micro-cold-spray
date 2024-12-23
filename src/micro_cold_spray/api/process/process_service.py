"""Process management service."""

from typing import List
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.process.models.process_models import (
    ExecutionStatus,
    ActionStatus,
    ProcessPattern,
    ParameterSet,
    SequenceMetadata,
    SequenceStep
)
from micro_cold_spray.api.process.services.action_service import ActionService
from micro_cold_spray.api.process.services.parameter_service import ParameterService
from micro_cold_spray.api.process.services.pattern_service import PatternService
from micro_cold_spray.api.process.services.sequence_service import SequenceService


class ProcessService:
    """Process management service."""

    def __init__(self) -> None:
        """Initialize service."""
        self._action_service = ActionService()
        self._parameter_service = ParameterService()
        self._pattern_service = PatternService()
        self._sequence_service = SequenceService()
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    async def initialize(self) -> None:
        """Initialize service.
        
        Raises:
            HTTPException: If initialization fails (503)
        """
        try:
            logger.info("Initializing process service")
            await self._action_service.initialize()
            await self._parameter_service.initialize()
            await self._pattern_service.initialize()
            await self._sequence_service.initialize()
            logger.info("Process service initialized")
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to initialize process service",
                context={"error": str(e)},
                cause=e
            )

    async def start(self) -> None:
        """Start service.
        
        Raises:
            HTTPException: If start fails (503)
        """
        try:
            logger.info("Starting process service")
            await self._action_service.start()
            await self._parameter_service.start()
            await self._pattern_service.start()
            await self._sequence_service.start()
            self._is_running = True
            logger.info("Process service started")
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to start process service",
                context={"error": str(e)},
                cause=e
            )

    async def stop(self) -> None:
        """Stop service.
        
        Raises:
            HTTPException: If stop fails (503)
        """
        try:
            logger.info("Stopping process service")
            await self._sequence_service.stop()
            await self._pattern_service.stop()
            await self._parameter_service.stop()
            await self._action_service.stop()
            self._is_running = False
            logger.info("Process service stopped")
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to stop process service",
                context={"error": str(e)},
                cause=e
            )

    async def get_status(self) -> ExecutionStatus:
        """Get execution status.
        
        Returns:
            Current execution status
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._action_service.get_status()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get status",
                context={"error": str(e)},
                cause=e
            )

    async def get_action_status(self, action_id: str) -> ActionStatus:
        """Get action status.
        
        Args:
            action_id: Action ID
            
        Returns:
            Action status
            
        Raises:
            HTTPException: If action not found (404) or service unavailable (503)
        """
        try:
            return await self._action_service.get_action_status(action_id)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get action status",
                context={"error": str(e), "action_id": action_id},
                cause=e
            )

    async def get_patterns(self) -> List[ProcessPattern]:
        """Get process patterns.
        
        Returns:
            List of process patterns
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._pattern_service.get_patterns()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get patterns",
                context={"error": str(e)},
                cause=e
            )

    async def get_pattern(self, pattern_id: str) -> ProcessPattern:
        """Get process pattern.
        
        Args:
            pattern_id: Pattern ID
            
        Returns:
            Process pattern
            
        Raises:
            HTTPException: If pattern not found (404) or service unavailable (503)
        """
        try:
            return await self._pattern_service.get_pattern(pattern_id)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get pattern",
                context={"error": str(e), "pattern_id": pattern_id},
                cause=e
            )

    async def create_pattern(self, pattern: ProcessPattern) -> None:
        """Create process pattern.
        
        Args:
            pattern: Process pattern
            
        Raises:
            HTTPException: If pattern exists (409) or service unavailable (503)
        """
        try:
            await self._pattern_service.create_pattern(pattern)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to create pattern",
                context={"error": str(e)},
                cause=e
            )

    async def update_pattern(self, pattern: ProcessPattern) -> None:
        """Update process pattern.
        
        Args:
            pattern: Process pattern
            
        Raises:
            HTTPException: If pattern not found (404) or service unavailable (503)
        """
        try:
            await self._pattern_service.update_pattern(pattern)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to update pattern",
                context={"error": str(e)},
                cause=e
            )

    async def delete_pattern(self, pattern_id: str) -> None:
        """Delete process pattern.
        
        Args:
            pattern_id: Pattern ID
            
        Raises:
            HTTPException: If pattern not found (404) or service unavailable (503)
        """
        try:
            await self._pattern_service.delete_pattern(pattern_id)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to delete pattern",
                context={"error": str(e), "pattern_id": pattern_id},
                cause=e
            )

    async def get_parameters(self) -> List[ParameterSet]:
        """Get parameter sets.
        
        Returns:
            List of parameter sets
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._parameter_service.get_parameters()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get parameters",
                context={"error": str(e)},
                cause=e
            )

    async def get_parameter(self, parameter_id: str) -> ParameterSet:
        """Get parameter set.
        
        Args:
            parameter_id: Parameter set ID
            
        Returns:
            Parameter set
            
        Raises:
            HTTPException: If parameter set not found (404) or service unavailable (503)
        """
        try:
            return await self._parameter_service.get_parameter(parameter_id)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get parameter",
                context={"error": str(e), "parameter_id": parameter_id},
                cause=e
            )

    async def create_parameter(self, parameter: ParameterSet) -> None:
        """Create parameter set.
        
        Args:
            parameter: Parameter set
            
        Raises:
            HTTPException: If parameter set exists (409) or service unavailable (503)
        """
        try:
            await self._parameter_service.create_parameter(parameter)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to create parameter",
                context={"error": str(e)},
                cause=e
            )

    async def update_parameter(self, parameter: ParameterSet) -> None:
        """Update parameter set.
        
        Args:
            parameter: Parameter set
            
        Raises:
            HTTPException: If parameter set not found (404) or service unavailable (503)
        """
        try:
            await self._parameter_service.update_parameter(parameter)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to update parameter",
                context={"error": str(e)},
                cause=e
            )

    async def delete_parameter(self, parameter_id: str) -> None:
        """Delete parameter set.
        
        Args:
            parameter_id: Parameter set ID
            
        Raises:
            HTTPException: If parameter set not found (404) or service unavailable (503)
        """
        try:
            await self._parameter_service.delete_parameter(parameter_id)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to delete parameter",
                context={"error": str(e), "parameter_id": parameter_id},
                cause=e
            )

    async def get_sequences(self) -> List[SequenceMetadata]:
        """Get sequence metadata.
        
        Returns:
            List of sequence metadata
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._sequence_service.get_sequences()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get sequences",
                context={"error": str(e)},
                cause=e
            )

    async def get_sequence(self, sequence_id: str) -> List[SequenceStep]:
        """Get sequence steps.
        
        Args:
            sequence_id: Sequence ID
            
        Returns:
            List of sequence steps
            
        Raises:
            HTTPException: If sequence not found (404) or service unavailable (503)
        """
        try:
            return await self._sequence_service.get_sequence(sequence_id)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get sequence",
                context={"error": str(e), "sequence_id": sequence_id},
                cause=e
            )

    async def create_sequence(self, sequence_id: str, steps: List[SequenceStep]) -> None:
        """Create sequence.
        
        Args:
            sequence_id: Sequence ID
            steps: Sequence steps
            
        Raises:
            HTTPException: If sequence exists (409) or service unavailable (503)
        """
        try:
            await self._sequence_service.create_sequence(sequence_id, steps)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to create sequence",
                context={"error": str(e), "sequence_id": sequence_id},
                cause=e
            )

    async def update_sequence(self, sequence_id: str, steps: List[SequenceStep]) -> None:
        """Update sequence.
        
        Args:
            sequence_id: Sequence ID
            steps: Sequence steps
            
        Raises:
            HTTPException: If sequence not found (404) or service unavailable (503)
        """
        try:
            await self._sequence_service.update_sequence(sequence_id, steps)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to update sequence",
                context={"error": str(e), "sequence_id": sequence_id},
                cause=e
            )

    async def delete_sequence(self, sequence_id: str) -> None:
        """Delete sequence.
        
        Args:
            sequence_id: Sequence ID
            
        Raises:
            HTTPException: If sequence not found (404) or service unavailable (503)
        """
        try:
            await self._sequence_service.delete_sequence(sequence_id)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to delete sequence",
                context={"error": str(e), "sequence_id": sequence_id},
                cause=e
            )
