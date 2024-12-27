"""Sequence service implementation."""

import os
import time
import yaml
from typing import Dict, Any, List, Optional
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.process.models.process_models import (
    ExecutionStatus,
    SequenceMetadata,
    SequenceStep
)


class SequenceService:
    """Service for managing process sequences."""

    def __init__(self):
        """Initialize sequence service."""
        self._start_time = time.time()
        self._is_running = False
        self._version = "1.0.0"
        self._service_name = "sequence"
        self._sequences: Dict[str, SequenceMetadata] = {}
        self._active_sequence: Optional[str] = None
        self._sequence_status = ExecutionStatus.IDLE

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
        return time.time() - self._start_time

    async def initialize(self) -> None:
        """Initialize service.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            logger.info("Initializing sequence service...")
            
            # Load config
            config_path = os.path.join("config", "process.yaml")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                    if "sequence" in config:
                        self._version = config["sequence"].get("version", self._version)
                        
                        # Load sequences from config
                        sequences = config["sequence"].get("sequences", {})
                        for seq_id, seq_data in sequences.items():
                            steps = []
                            for step_data in seq_data.get("steps", []):
                                steps.append(SequenceStep(
                                    name=step_data.get("name", ""),
                                    description=step_data.get("description", ""),
                                    pattern_id=step_data.get("pattern_id", ""),
                                    parameter_set_id=step_data.get("parameter_set_id", "")
                                ))
                                
                            self._sequences[seq_id] = SequenceMetadata(
                                id=seq_id,
                                name=seq_data.get("name", ""),
                                description=seq_data.get("description", ""),
                                steps=steps
                            )
            
            logger.info("Sequence service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize sequence service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def start(self) -> None:
        """Start service.
        
        Raises:
            Exception: If start fails
        """
        try:
            logger.info("Starting sequence service...")
            self._is_running = True
            logger.info("Sequence service started")
            
        except Exception as e:
            error_msg = f"Failed to start sequence service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def stop(self) -> None:
        """Stop service.
        
        Raises:
            Exception: If stop fails
        """
        try:
            logger.info("Stopping sequence service...")
            
            # Stop active sequence if any
            if self._active_sequence:
                await self.stop_sequence(self._active_sequence)
            
            self._is_running = False
            logger.info("Sequence service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop sequence service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def health(self) -> ServiceHealth:
        """Get service health status.
        
        Returns:
            ServiceHealth: Service health status
        """
        try:
            status = "healthy"
            error = None
            
            if not self.is_running:
                status = "error"
                error = "Service not running"
            elif self._sequence_status == ExecutionStatus.ERROR:
                status = "error"
                error = "Sequence in error state"
            elif self._sequence_status == ExecutionStatus.RUNNING:
                status = "degraded"
                error = "Sequence in progress"
                
            return ServiceHealth(
                status=status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=error,
                components={}
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
                components={}
            )

    async def list_sequences(self) -> List[SequenceMetadata]:
        """List available sequences.
        
        Returns:
            List[SequenceMetadata]: List of sequences
            
        Raises:
            Exception: If listing fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            return list(self._sequences.values())
            
        except Exception as e:
            error_msg = "Failed to list sequences"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)

    async def get_sequence(self, sequence_id: str) -> SequenceMetadata:
        """Get sequence by ID.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            SequenceMetadata: Sequence metadata
            
        Raises:
            Exception: If sequence not found or retrieval fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if sequence_id not in self._sequences:
                raise Exception(f"Sequence {sequence_id} not found")
                
            return self._sequences[sequence_id]
            
        except Exception as e:
            error_msg = f"Failed to get sequence {sequence_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)

    async def start_sequence(self, sequence_id: str) -> ExecutionStatus:
        """Start sequence execution.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            ExecutionStatus: Sequence execution status
            
        Raises:
            Exception: If start fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if self._active_sequence:
                raise Exception(f"Sequence {self._active_sequence} already in progress")
                
            if sequence_id not in self._sequences:
                raise Exception(f"Sequence {sequence_id} not found")
                
            self._active_sequence = sequence_id
            self._sequence_status = ExecutionStatus.RUNNING
            logger.info(f"Started sequence {sequence_id}")
            
            return self._sequence_status
            
        except Exception as e:
            error_msg = f"Failed to start sequence {sequence_id}"
            logger.error(f"{error_msg}: {str(e)}")
            self._sequence_status = ExecutionStatus.ERROR
            raise Exception(error_msg)

    async def stop_sequence(self, sequence_id: str) -> ExecutionStatus:
        """Stop sequence execution.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            ExecutionStatus: Sequence execution status
            
        Raises:
            Exception: If stop fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if not self._active_sequence:
                raise Exception("No sequence in progress")
                
            if sequence_id != self._active_sequence:
                raise Exception(f"Sequence {sequence_id} not in progress")
                
            self._active_sequence = None
            self._sequence_status = ExecutionStatus.IDLE
            logger.info(f"Stopped sequence {sequence_id}")
            
            return self._sequence_status
            
        except Exception as e:
            error_msg = f"Failed to stop sequence {sequence_id}"
            logger.error(f"{error_msg}: {str(e)}")
            self._sequence_status = ExecutionStatus.ERROR
            raise Exception(error_msg)

    async def get_sequence_status(self, sequence_id: str) -> ExecutionStatus:
        """Get sequence execution status.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            ExecutionStatus: Sequence execution status
            
        Raises:
            Exception: If status check fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if not self._active_sequence:
                return ExecutionStatus.IDLE
                
            if sequence_id != self._active_sequence:
                raise Exception(f"Sequence {sequence_id} not found")
                
            return self._sequence_status
            
        except Exception as e:
            error_msg = f"Failed to get status for sequence {sequence_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)
