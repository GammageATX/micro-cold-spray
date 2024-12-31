"""Sequence service implementation."""

import os
import time
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import status
from loguru import logger
from pathlib import Path

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.process.models.process_models import (
    ExecutionStatus,
    SequenceMetadata,
    SequenceStep,
    Action,
    Sequence
)


class SequenceService:
    """Service for managing process sequences."""

    def __init__(self, version: str = "1.0.0"):
        """Initialize sequence service."""
        self._service_name = "sequence"
        self._version = version
        self._is_running = False
        self._start_time = None
        
        # Initialize components to None
        self._sequences = None
        self._failed_sequences = {}  # Track failed sequences
        self._active_sequence = None
        self._sequence_status = ExecutionStatus.IDLE
        
        logger.info(f"{self.service_name} service initialized")

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            # Initialize sequences
            self._sequences = {}
            
            # Load sequences from config
            await self._load_sequences()
            
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def _load_sequences(self) -> None:
        """Load sequences from files."""
        try:
            sequence_dir = Path("data/sequences")
            if not sequence_dir.exists():
                return
            
            for sequence_file in sequence_dir.glob("*.yaml"):
                try:
                    with open(sequence_file, "r") as f:
                        data = yaml.safe_load(f)
                    
                    if "sequence" not in data:
                        logger.error(f"Missing 'sequence' root key in {sequence_file}")
                        continue
                    
                    sequence_data = data["sequence"]
                    steps = [SequenceStep(**step) for step in sequence_data["steps"]]
                    metadata = SequenceMetadata(**sequence_data["metadata"])
                    
                    sequence = {
                        "metadata": metadata,
                        "steps": steps
                    }
                    
                    self._sequences[metadata.name] = sequence
                    logger.info(f"Loaded sequence: {metadata.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to load sequence {sequence_file}: {e}")
                    continue
                
        except Exception as e:
            logger.error(f"Failed to load sequences: {e}")

    async def _attempt_recovery(self) -> None:
        """Attempt to recover failed sequences."""
        if self._failed_sequences:
            logger.info(f"Attempting to recover {len(self._failed_sequences)} failed sequences...")
            await self._load_sequences()

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            # Set service as running
            self._is_running = True
            self._start_time = datetime.now()
            
            logger.info(f"{self.service_name} service started")
            
        except Exception as e:
            self._is_running = False
            self._start_time = None
            error_msg = f"Failed to start {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service not running"
                )
            
            # 1. Stop active sequences
            if self._active_sequence:
                await self.stop_sequence(self._active_sequence)
            
            # 2. Clear sequence data
            self._sequences.clear()
            self._active_sequence = None
            self._sequence_status = ExecutionStatus.IDLE
            
            # 3. Reset service state
            self._is_running = False
            self._start_time = None
            
            logger.info(f"{self.service_name} service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def health(self) -> ServiceHealth:
        """Get service health status."""
        try:
            # Attempt recovery of failed sequences
            await self._attempt_recovery()
            
            # Check component health
            sequence_status = "ok"
            sequence_error = None
            
            if self._sequence_status == ExecutionStatus.ERROR:
                sequence_status = "error"
                sequence_error = "Sequence in error state"
            elif self._sequence_status == ExecutionStatus.RUNNING:
                sequence_status = "degraded"
                sequence_error = "Sequence in progress"
            
            components = {
                "sequence": ComponentHealth(
                    status=sequence_status,
                    error=sequence_error
                ),
                "sequences": ComponentHealth(
                    status="ok" if self._sequences is not None and len(self._sequences) > 0 else "error",
                    error=None if self._sequences is not None and len(self._sequences) > 0 else "No sequences loaded"
                )
            }
            
            # Add failed sequences component if any exist
            if self._failed_sequences:
                failed_list = ", ".join(self._failed_sequences.keys())
                components["failed_sequences"] = ComponentHealth(
                    status="error",
                    error=f"Failed sequences: {failed_list}"
                )
            
            # Overall status is error only if no sequences loaded
            overall_status = "error" if not self._sequences or len(self._sequences) == 0 else "ok"
            if not self.is_running:
                overall_status = "error"
            
            return ServiceHealth(
                status=overall_status,
                service=self.service_name,
                version=self.version,
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
                service=self.service_name,
                version=self.version,
                is_running=False,
                uptime=self.uptime,
                error=error_msg,
                components={name: ComponentHealth(status="error", error=error_msg)
                            for name in ["sequence", "sequences"]}
            )

    async def list_sequences(self) -> List[Sequence]:
        """List available sequences.
        
        Returns:
            List[Sequence]: List of sequences
            
        Raises:
            HTTPException: If service not running or listing fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
            
            sequences = list(self._sequences.values())
            logger.info(f"Retrieved {len(sequences)} sequences")
            return sequences
            
        except Exception as e:
            error_msg = "Failed to list sequences"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def get_sequence(self, sequence_id: str) -> Sequence:
        """Get sequence by ID.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            Sequence: Sequence if found
            
        Raises:
            HTTPException: If service not running or sequence not found
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
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start_sequence(self, sequence_id: str) -> ExecutionStatus:
        """Start sequence execution."""
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
                
            if self._active_sequence:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Sequence {self._active_sequence} already in progress"
                )
                
            self._active_sequence = sequence_id
            self._sequence_status = ExecutionStatus.RUNNING
            logger.info(f"Started sequence {sequence_id}")
            
            return self._sequence_status
            
        except Exception as e:
            error_msg = f"Failed to start sequence {sequence_id}"
            logger.error(f"{error_msg}: {str(e)}")
            self._sequence_status = ExecutionStatus.ERROR
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop_sequence(self, sequence_id: str) -> ExecutionStatus:
        """Stop sequence execution."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if not self._active_sequence:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="No sequence in progress"
                )
                
            if sequence_id != self._active_sequence:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not in progress"
                )
                
            self._active_sequence = None
            self._sequence_status = ExecutionStatus.IDLE
            logger.info(f"Stopped sequence {sequence_id}")
            
            return self._sequence_status
            
        except Exception as e:
            error_msg = f"Failed to stop sequence {sequence_id}"
            logger.error(f"{error_msg}: {str(e)}")
            self._sequence_status = ExecutionStatus.ERROR
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def get_sequence_status(self, sequence_id: str) -> ExecutionStatus:
        """Get sequence execution status."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if not self._active_sequence:
                return ExecutionStatus.IDLE
                
            if sequence_id != self._active_sequence:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not found"
                )
                
            return self._sequence_status
            
        except Exception as e:
            error_msg = f"Failed to get status for sequence {sequence_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )
