"""Process management service."""

from typing import List, Optional
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
        self._current_sequence: Optional[str] = None
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
            if not self._is_running:
                return ExecutionStatus.IDLE
                
            if self._current_sequence:
                action_status = await self._action_service.get_status()
                if action_status == ActionStatus.RUNNING:
                    return ExecutionStatus.RUNNING
                elif action_status == ActionStatus.COMPLETED:
                    return ExecutionStatus.COMPLETED
                elif action_status == ActionStatus.FAILED:
                    return ExecutionStatus.ERROR
                elif action_status == ActionStatus.ERROR:
                    return ExecutionStatus.ERROR
                
            return ExecutionStatus.IDLE
            
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get status",
                context={"error": str(e)},
                cause=e
            )

    async def get_current_sequence(self) -> Optional[SequenceMetadata]:
        """Get current sequence.
        
        Returns:
            Current sequence if running, None otherwise
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            if not self._current_sequence:
                return None
                
            return await self._sequence_service.get_sequence(self._current_sequence)
            
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get current sequence",
                context={"error": str(e)},
                cause=e
            )

    async def start_sequence(self, sequence_id: str) -> None:
        """Start sequence execution.
        
        Args:
            sequence_id: Sequence ID to start
            
        Raises:
            HTTPException: If sequence not found (404) or service unavailable (503)
        """
        try:
            # Check if sequence exists
            sequence = await self._sequence_service.get_sequence(sequence_id)
            if not sequence:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not found",
                    context={"sequence_id": sequence_id}
                )
                
            # Check if already running
            if self._current_sequence:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Another sequence is already running",
                    context={"sequence_id": self._current_sequence}
                )
                
            # Start sequence
            self._current_sequence = sequence_id
            logger.info(f"Started sequence: {sequence_id}")
            
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to start sequence",
                context={"error": str(e), "sequence_id": sequence_id},
                cause=e
            )

    async def stop_sequence(self, sequence_id: str) -> None:
        """Stop sequence execution.
        
        Args:
            sequence_id: Sequence ID to stop
            
        Raises:
            HTTPException: If sequence not found (404) or service unavailable (503)
        """
        try:
            # Check if sequence exists
            sequence = await self._sequence_service.get_sequence(sequence_id)
            if not sequence:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not found",
                    context={"sequence_id": sequence_id}
                )
                
            # Check if running
            if not self._current_sequence:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="No sequence is running",
                    context={"sequence_id": sequence_id}
                )
                
            if self._current_sequence != sequence_id:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Sequence {sequence_id} is not running",
                    context={
                        "sequence_id": sequence_id,
                        "current_sequence": self._current_sequence
                    }
                )
                
            # Stop sequence
            await self._action_service.stop_action()
            self._current_sequence = None
            logger.info(f"Stopped sequence: {sequence_id}")
            
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to stop sequence",
                context={"error": str(e), "sequence_id": sequence_id},
                cause=e
            )

    async def get_sequences(self) -> List[SequenceMetadata]:
        """Get sequences.
        
        Returns:
            List of sequences
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._sequence_service.list_sequences()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get sequences",
                context={"error": str(e)},
                cause=e
            )

    async def get_sequence(self, sequence_id: str) -> Optional[SequenceMetadata]:
        """Get sequence.
        
        Args:
            sequence_id: Sequence ID
            
        Returns:
            Sequence if found, None otherwise
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._sequence_service.get_sequence(sequence_id)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get sequence",
                context={"error": str(e), "sequence_id": sequence_id},
                cause=e
            )

    async def create_sequence(self, sequence: SequenceMetadata) -> None:
        """Create sequence.
        
        Args:
            sequence: Sequence to create
            
        Raises:
            HTTPException: If sequence exists (409) or service unavailable (503)
        """
        try:
            await self._sequence_service.create_sequence(sequence)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to create sequence",
                context={"error": str(e)},
                cause=e
            )

    async def update_sequence(self, sequence: SequenceMetadata) -> None:
        """Update sequence.
        
        Args:
            sequence: Sequence to update
            
        Raises:
            HTTPException: If sequence not found (404) or service unavailable (503)
        """
        try:
            await self._sequence_service.update_sequence(sequence)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to update sequence",
                context={"error": str(e)},
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

    async def get_patterns(self) -> List[ProcessPattern]:
        """Get patterns.
        
        Returns:
            List of patterns
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._pattern_service.list_patterns()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get patterns",
                context={"error": str(e)},
                cause=e
            )

    async def get_pattern(self, pattern_id: str) -> Optional[ProcessPattern]:
        """Get pattern.
        
        Args:
            pattern_id: Pattern ID
            
        Returns:
            Pattern if found, None otherwise
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._pattern_service.get_pattern(pattern_id)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get pattern",
                context={"error": str(e), "pattern_id": pattern_id},
                cause=e
            )

    async def create_pattern(self, pattern: ProcessPattern) -> None:
        """Create pattern.
        
        Args:
            pattern: Pattern to create
            
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
        """Update pattern.
        
        Args:
            pattern: Pattern to update
            
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
        """Delete pattern.
        
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
        """Get parameters.
        
        Returns:
            List of parameters
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._parameter_service.list_parameter_sets()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get parameters",
                context={"error": str(e)},
                cause=e
            )

    async def get_parameter(self, parameter_id: str) -> Optional[ParameterSet]:
        """Get parameter.
        
        Args:
            parameter_id: Parameter ID
            
        Returns:
            Parameter if found, None otherwise
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._parameter_service.get_parameter_set(parameter_id)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get parameter",
                context={"error": str(e), "parameter_id": parameter_id},
                cause=e
            )

    async def create_parameter(self, parameter: ParameterSet) -> None:
        """Create parameter.
        
        Args:
            parameter: Parameter to create
            
        Raises:
            HTTPException: If parameter exists (409) or service unavailable (503)
        """
        try:
            await self._parameter_service.create_parameter_set(parameter)
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
        """Update parameter.
        
        Args:
            parameter: Parameter to update
            
        Raises:
            HTTPException: If parameter not found (404) or service unavailable (503)
        """
        try:
            await self._parameter_service.update_parameter_set(parameter)
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
        """Delete parameter.
        
        Args:
            parameter_id: Parameter ID
            
        Raises:
            HTTPException: If parameter not found (404) or service unavailable (503)
        """
        try:
            await self._parameter_service.delete_parameter_set(parameter_id)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to delete parameter",
                context={"error": str(e), "parameter_id": parameter_id},
                cause=e
            )
