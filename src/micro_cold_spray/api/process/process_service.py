"""Process management service."""

from typing import List, Optional, Dict, Any
from datetime import datetime
import time
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
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
    """Service for managing process execution."""

    def __init__(self):
        """Initialize process service."""
        self._service_name = "process"
        self._version = "1.0.0"
        self._start_time = None
        self._is_running = False
        
        # Initialize sub-services
        self._action = ActionService()
        self._parameter = ParameterService()
        self._pattern = PatternService()
        self._sequence = SequenceService()
        
        logger.info("ProcessService initialized")

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
        """Initialize service and sub-services."""
        try:
            # Initialize sub-services
            await self._action.initialize()
            await self._parameter.initialize()
            await self._pattern.initialize()
            await self._sequence.initialize()
            
            logger.info("Process service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize process service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"error": str(e)}
            )

    async def start(self) -> None:
        """Start process service and sub-services."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Start sub-services
            await self._action.start()
            await self._parameter.start()
            await self._pattern.start()
            await self._sequence.start()

            self._start_time = datetime.now()
            self._is_running = True
            logger.info("Process service started")

        except Exception as e:
            error_msg = f"Failed to start process service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"error": str(e)}
            )

    async def stop(self) -> None:
        """Stop process service and sub-services."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service not running"
                )

            # Stop sub-services
            await self._sequence.stop()
            await self._pattern.stop()
            await self._parameter.stop()
            await self._action.stop()

            self._is_running = False
            self._start_time = None
            logger.info("Process service stopped")

        except Exception as e:
            error_msg = f"Failed to stop process service: {str(e)}"
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
            "sub_services": {
                "action": await self._action.health(),
                "parameter": await self._parameter.health(),
                "pattern": await self._pattern.health(),
                "sequence": await self._sequence.health()
            }
        }

    # Process management methods
    async def list_sequences(self) -> List[SequenceMetadata]:
        """List available sequences.
        
        Returns:
            List of sequence metadata
            
        Raises:
            HTTPException: If listing fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
            return await self._sequence.list_sequences()
        except Exception as e:
            error_msg = "Failed to list sequences"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )

    async def get_sequence(self, sequence_id: str) -> SequenceMetadata:
        """Get sequence by ID.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            Sequence metadata
            
        Raises:
            HTTPException: If sequence not found or retrieval fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
            return await self._sequence.get_sequence(sequence_id)
        except Exception as e:
            error_msg = f"Failed to get sequence {sequence_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )

    async def start_sequence(self, sequence_id: str) -> ExecutionStatus:
        """Start sequence execution.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            Execution status
            
        Raises:
            HTTPException: If start fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
            return await self._sequence.start_sequence(sequence_id)
        except Exception as e:
            error_msg = f"Failed to start sequence {sequence_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )

    async def stop_sequence(self, sequence_id: str) -> ExecutionStatus:
        """Stop sequence execution.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            Execution status
            
        Raises:
            HTTPException: If stop fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
            return await self._sequence.stop_sequence(sequence_id)
        except Exception as e:
            error_msg = f"Failed to stop sequence {sequence_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )

    async def get_sequence_status(self, sequence_id: str) -> ExecutionStatus:
        """Get sequence execution status.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            Execution status
            
        Raises:
            HTTPException: If status check fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
            return await self._sequence.get_sequence_status(sequence_id)
        except Exception as e:
            error_msg = f"Failed to get status for sequence {sequence_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )
