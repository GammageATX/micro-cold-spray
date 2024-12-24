"""Sequence service for process execution."""

from datetime import datetime
import time
from typing import Dict, List, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.process.models.process_models import (
    ExecutionStatus,
    SequenceMetadata,
    SequenceStep
)


class SequenceService:
    """Service for managing process sequences."""

    def __init__(self):
        """Initialize sequence service."""
        self._service_name = "sequence"
        self._version = "1.0.0"
        self._start_time = None
        self._is_running = False
        self._sequences: Dict[str, SequenceMetadata] = {}
        self._current_sequence = None
        logger.info("SequenceService initialized")

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
            logger.info("Sequence service initialized")
        except Exception as e:
            error_msg = f"Failed to initialize sequence service: {str(e)}"
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
            logger.info("Sequence service started")

        except Exception as e:
            error_msg = f"Failed to start sequence service: {str(e)}"
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
            logger.info("Sequence service stopped")

        except Exception as e:
            error_msg = f"Failed to stop sequence service: {str(e)}"
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
            "sequence_count": len(self._sequences),
            "current_sequence": self._current_sequence
        }

    async def list_sequences(self) -> List[SequenceMetadata]:
        """List available sequences.
        
        Returns:
            List of sequences
            
        Raises:
            HTTPException: If listing fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
            return list(self._sequences.values())
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

            if sequence_id not in self._sequences:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not found"
                )

            return self._sequences[sequence_id]
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
            HTTPException: If sequence not found or start fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if sequence_id not in self._sequences:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not found"
                )

            if self._current_sequence:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Another sequence is already running",
                    context={"current_sequence": self._current_sequence}
                )

            self._current_sequence = sequence_id
            logger.info(f"Started sequence: {sequence_id}")
            return ExecutionStatus.RUNNING

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
            HTTPException: If sequence not found or stop fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if sequence_id not in self._sequences:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not found"
                )

            if not self._current_sequence:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="No sequence is running"
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

            self._current_sequence = None
            logger.info(f"Stopped sequence: {sequence_id}")
            return ExecutionStatus.COMPLETED

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
            HTTPException: If sequence not found or status check fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if sequence_id not in self._sequences:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not found"
                )

            if not self._current_sequence:
                return ExecutionStatus.IDLE

            if self._current_sequence != sequence_id:
                return ExecutionStatus.IDLE

            return ExecutionStatus.RUNNING

        except Exception as e:
            error_msg = f"Failed to get status for sequence {sequence_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )
