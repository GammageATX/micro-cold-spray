"""Process service implementation."""

import os
import time
import yaml
from typing import Dict, Any, List, Optional
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
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


def load_config() -> Dict[str, Any]:
    """Load process configuration.
    
    Returns:
        Dict[str, Any]: Configuration data
    """
    config_path = os.path.join("config", "process.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {"version": "1.0.0"}


class ProcessService:
    """Process service for managing process execution."""

    def __init__(self):
        """Initialize process service."""
        # Load config
        config = load_config()
        process_config = config.get("process", {})
        
        self._start_time = time.time()
        self._is_running = False
        self._version = process_config.get("version", "1.0.0")
        self._service_name = "process"

        # Initialize sub-services
        self._action = ActionService()
        self._parameter = ParameterService()
        self._pattern = PatternService()
        self._sequence = SequenceService()

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
        """Initialize service and sub-services.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            logger.info("Initializing process service...")
            
            # Initialize sub-services
            await self._action.initialize()
            await self._parameter.initialize()
            await self._pattern.initialize()
            await self._sequence.initialize()
            
            logger.info("Process service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize process service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def start(self) -> None:
        """Start service and sub-services.
        
        Raises:
            Exception: If start fails
        """
        try:
            logger.info("Starting process service...")
            
            # Start sub-services
            await self._action.start()
            await self._parameter.start()
            await self._pattern.start()
            await self._sequence.start()
            
            self._is_running = True
            logger.info("Process service started")
            
        except Exception as e:
            error_msg = f"Failed to start process service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def stop(self) -> None:
        """Stop service and sub-services.
        
        Raises:
            Exception: If stop fails
        """
        try:
            logger.info("Stopping process service...")
            
            # Stop sub-services
            await self._action.stop()
            await self._parameter.stop()
            await self._pattern.stop()
            await self._sequence.stop()
            
            self._is_running = False
            logger.info("Process service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop process service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def health(self) -> ServiceHealth:
        """Get service health status.
        
        Returns:
            ServiceHealth: Service health status
        """
        try:
            # Get sub-service health
            action_health = await self._action.health()
            parameter_health = await self._parameter.health()
            pattern_health = await self._pattern.health()
            sequence_health = await self._sequence.health()

            # Determine overall status
            status = "healthy"
            error = None
            
            if not all(h.status == "healthy" for h in [action_health, parameter_health, pattern_health, sequence_health]):
                status = "degraded"
                error = "One or more components are unhealthy"

            return ServiceHealth(
                status=status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=error,
                components={
                    "action": {
                        "status": action_health.status,
                        "error": action_health.error
                    },
                    "parameter": {
                        "status": parameter_health.status,
                        "error": parameter_health.error
                    },
                    "pattern": {
                        "status": pattern_health.status,
                        "error": pattern_health.error
                    },
                    "sequence": {
                        "status": sequence_health.status,
                        "error": sequence_health.error
                    }
                }
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
                components={
                    "action": {"status": "error", "error": error_msg},
                    "parameter": {"status": "error", "error": error_msg},
                    "pattern": {"status": "error", "error": error_msg},
                    "sequence": {"status": "error", "error": error_msg}
                }
            )

    async def list_sequences(self) -> List[SequenceMetadata]:
        """List available sequences.
        
        Returns:
            List[SequenceMetadata]: List of sequence metadata
            
        Raises:
            Exception: If listing fails
        """
        return await self._sequence.list_sequences()

    async def get_sequence(self, sequence_id: str) -> SequenceMetadata:
        """Get sequence by ID.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            SequenceMetadata: Sequence metadata
            
        Raises:
            Exception: If sequence not found or retrieval fails
        """
        return await self._sequence.get_sequence(sequence_id)

    async def start_sequence(self, sequence_id: str) -> ExecutionStatus:
        """Start sequence execution.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            ExecutionStatus: Sequence execution status
            
        Raises:
            Exception: If start fails
        """
        return await self._sequence.start_sequence(sequence_id)

    async def stop_sequence(self, sequence_id: str) -> ExecutionStatus:
        """Stop sequence execution.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            ExecutionStatus: Sequence execution status
            
        Raises:
            Exception: If stop fails
        """
        return await self._sequence.stop_sequence(sequence_id)

    async def get_sequence_status(self, sequence_id: str) -> ExecutionStatus:
        """Get sequence execution status.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            ExecutionStatus: Sequence execution status
            
        Raises:
            Exception: If status check fails
        """
        return await self._sequence.get_sequence_status(sequence_id)
