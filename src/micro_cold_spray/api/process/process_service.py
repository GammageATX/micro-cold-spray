"""Process service for managing process execution."""

from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.process.services.parameter_service import ParameterService
from micro_cold_spray.api.process.services.pattern_service import PatternService
from micro_cold_spray.api.process.services.action_service import ActionService
from micro_cold_spray.api.process.services.sequence_service import SequenceService


class ProcessService:
    """Process service for managing process execution."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize process service.
        
        Args:
            config: Service configuration
        """
        self._config = config
        self._version = config.get("version", "1.0.0")
        self._initialized = False
        self._running = False
        self._start_time: Optional[datetime] = None
        
        # Sub-services initialized lazily
        self._parameter: Optional[ParameterService] = None
        self._pattern: Optional[PatternService] = None
        self._action: Optional[ActionService] = None
        self._sequence: Optional[SequenceService] = None

    @property
    def parameter_service(self) -> ParameterService:
        """Get parameter service instance."""
        if not self._parameter:
            self._parameter = ParameterService(self._config)
        return self._parameter

    @property
    def pattern_service(self) -> PatternService:
        """Get pattern service instance."""
        if not self._pattern:
            self._pattern = PatternService(self._config)
        return self._pattern

    @property
    def action_service(self) -> ActionService:
        """Get action service instance."""
        if not self._action:
            self._action = ActionService(self._config)
        return self._action

    @property
    def sequence_service(self) -> SequenceService:
        """Get sequence service instance."""
        if not self._sequence:
            self._sequence = SequenceService(self._config)
        return self._sequence

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._running

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        if not self._start_time:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds()

    async def get_health(self) -> ServiceHealth:
        """Get service health status."""
        components = {}
        
        # Check sub-service health
        for name, service in [
            ("parameter", self._parameter),
            ("pattern", self._pattern),
            ("action", self._action),
            ("sequence", self._sequence)
        ]:
            if service:
                try:
                    await service.get_health()
                    components[name] = ComponentHealth(status="ok")
                except Exception as e:
                    components[name] = ComponentHealth(
                        status="error",
                        error=str(e)
                    )
            else:
                components[name] = ComponentHealth(
                    status="ok",
                    error="Not initialized"
                )

        return ServiceHealth(
            status="ok" if self._running else "error",
            service=self._service_name,
            version=self._version,
            is_running=self._running,
            uptime=self.uptime,
            mode=self._config.get("mode", "normal"),
            error=None if self._running else "Service not running",
            components=components
        )

    async def initialize(self) -> None:
        """Initialize process service."""
        try:
            if self._initialized:
                return

            logger.info("Initializing process service...")
            
            # Initialize sub-services lazily
            if self._parameter:
                await self._parameter.initialize()
            if self._pattern:
                await self._pattern.initialize()
            if self._action:
                await self._action.initialize()
            if self._sequence:
                await self._sequence.initialize()
            
            self._initialized = True
            logger.info("Process service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize process service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to initialize service: {str(e)}"
            )

    async def start(self) -> None:
        """Start process service."""
        try:
            if not self._initialized:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service not initialized"
                )

            logger.info("Starting process service...")
            
            # Start sub-services
            if self._parameter:
                await self._parameter.start()
            if self._pattern:
                await self._pattern.start()
            if self._action:
                await self._action.start()
            if self._sequence:
                await self._sequence.start()
            
            self._running = True
            self._start_time = datetime.now()
            logger.info("Process service started")
            
        except Exception as e:
            logger.error(f"Failed to start process service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start service: {str(e)}"
            )

    async def stop(self) -> None:
        """Stop process service."""
        try:
            if not self._running:
                return

            logger.info("Stopping process service...")
            
            # Stop services in reverse order
            if self._sequence:
                await self._sequence.stop()
            if self._action:
                await self._action.stop()
            if self._pattern:
                await self._pattern.stop()
            if self._parameter:
                await self._parameter.stop()
            
            self._running = False
            self._start_time = None
            logger.info("Process service stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop process service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to stop service: {str(e)}"
            )
