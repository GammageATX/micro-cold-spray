"""Process service implementation."""

import os
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
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
    """Process service for managing process execution."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize process service.
        
        Args:
            config: Service configuration
        """
        self._service_name = "process"
        self._config = config
        self._version = config.get("version", "1.0.0")
        self._is_running = False
        self._mode = config.get("mode", "normal")
        self._start_time = None
        
        # Initialize component services to None
        self._action = None
        self._parameter = None
        self._pattern = None
        self._sequence = None
        self._failed_components = {}  # Track failed components
        
        logger.info(f"{self._service_name} service initialized")

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

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
            
            logger.info(f"Initializing {self.service_name} service...")
            
            # Initialize components in dependency order
            try:
                self._parameter = ParameterService()
                await self._parameter.initialize()
                self._failed_components.pop("parameter", None)
            except Exception as e:
                self._failed_components["parameter"] = str(e)
                logger.warning(f"Failed to initialize parameter service: {e}")
            
            try:
                self._pattern = PatternService()
                await self._pattern.initialize()
                self._failed_components.pop("pattern", None)
            except Exception as e:
                self._failed_components["pattern"] = str(e)
                logger.warning(f"Failed to initialize pattern service: {e}")
            
            try:
                self._action = ActionService()
                await self._action.initialize()
                self._failed_components.pop("action", None)
            except Exception as e:
                self._failed_components["action"] = str(e)
                logger.warning(f"Failed to initialize action service: {e}")
            
            try:
                self._sequence = SequenceService()
                await self._sequence.initialize()
                self._failed_components.pop("sequence", None)
            except Exception as e:
                self._failed_components["sequence"] = str(e)
                logger.warning(f"Failed to initialize sequence service: {e}")
            
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            if not all([self._parameter, self._pattern, self._action, self._sequence]):
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"{self.service_name} service not initialized"
                )
            
            logger.info(f"Starting {self.service_name} service...")
            
            # Start services in dependency order
            await self._parameter.start()
            await self._pattern.start()
            await self._action.start()
            await self._sequence.start()
            
            self._is_running = True
            self._start_time = datetime.now()
            logger.info(f"{self.service_name} service started successfully")
            
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
            
            # Stop services in reverse dependency order
            await self._sequence.stop()
            await self._action.stop()
            await self._pattern.stop()
            await self._parameter.stop()
            
            # Clear service references
            self._sequence = None
            self._action = None
            self._pattern = None
            self._parameter = None
            
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
            # Get health from components
            parameter_health = await self._parameter.health() if self._parameter else None
            pattern_health = await self._pattern.health() if self._pattern else None
            action_health = await self._action.health() if self._action else None
            sequence_health = await self._sequence.health() if self._sequence else None
            
            # Build component statuses
            components = {
                "parameter": ComponentHealth(
                    status="ok" if parameter_health and parameter_health.status == "ok" else "warning",
                    error=parameter_health.error if parameter_health else "Component not initialized"
                ),
                "pattern": ComponentHealth(
                    status="ok" if pattern_health and pattern_health.status == "ok" else "warning",
                    error=pattern_health.error if pattern_health else "Component not initialized"
                ),
                "action": ComponentHealth(
                    status="ok" if action_health and action_health.status == "ok" else "warning",
                    error=action_health.error if action_health else "Component not initialized"
                ),
                "sequence": ComponentHealth(
                    status="ok" if sequence_health and sequence_health.status == "ok" else "warning",
                    error=sequence_health.error if sequence_health else "Component not initialized"
                )
            }
            
            # Overall status is ok if at least one component is ok
            overall_status = "ok" if any(c.status == "ok" for c in components.values()) else "error"
            
            return ServiceHealth(
                status=overall_status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if overall_status == "ok" else "One or more components in warning state",
                mode=self._mode,
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
                mode=self._mode,
                components={name: ComponentHealth(status="error", error=error_msg)
                            for name in ["parameter", "pattern", "action", "sequence"]}
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
