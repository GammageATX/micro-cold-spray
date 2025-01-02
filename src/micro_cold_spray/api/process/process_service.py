"""Process service implementation."""

from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.process.services import (
    PatternService,
    ParameterService,
    SequenceService,
    SchemaService
)


class ProcessService:
    """Service for managing process execution."""

    def __init__(self, version: str = "1.0.0"):
        """Initialize process service."""
        self._service_name = "process"
        self._version = version
        self._is_running = False
        self._start_time = None

        # Initialize sub-services
        self.pattern_service = PatternService()
        self.parameter_service = ParameterService()
        self.sequence_service = SequenceService()
        self.schema_service = SchemaService()

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            logger.info("Initializing process service...")
            
            # Initialize sub-services
            await self.pattern_service.initialize()
            await self.parameter_service.initialize()
            await self.sequence_service.initialize()
            await self.schema_service.initialize()
            
            logger.info("Process service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize process service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start service."""
        try:
            logger.info("Starting process service...")
            
            # Start sub-services
            await self.pattern_service.start()
            await self.parameter_service.start()
            await self.sequence_service.start()
            await self.schema_service.start()
            
            self._is_running = True
            self._start_time = datetime.now()
            logger.info("Process service started")
            
        except Exception as e:
            error_msg = f"Failed to start process service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    async def shutdown(self) -> None:
        """Shutdown service."""
        try:
            logger.info("Shutting down process service...")
            
            # Stop sub-services
            if self.pattern_service.is_running:
                await self.pattern_service.stop()
            if self.parameter_service.is_running:
                await self.parameter_service.stop()
            if self.sequence_service.is_running:
                await self.sequence_service.stop()
            if self.schema_service.is_running:
                await self.schema_service.stop()
            
            self._is_running = False
            self._start_time = None
            logger.info("Process service shutdown complete")
            
        except Exception as e:
            error_msg = f"Failed to shutdown process service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def health(self) -> ServiceHealth:
        """Get service health status."""
        try:
            # Get component health status
            pattern_health = await self.pattern_service.health()
            parameter_health = await self.parameter_service.health()
            sequence_health = await self.sequence_service.health()
            schema_health = await self.schema_service.health()
            
            # Create components dict with ComponentHealth objects
            components = {
                "pattern": ComponentHealth(
                    status=pattern_health.status,
                    error=pattern_health.error
                ),
                "parameter": ComponentHealth(
                    status=parameter_health.status,
                    error=parameter_health.error
                ),
                "sequence": ComponentHealth(
                    status=sequence_health.status,
                    error=sequence_health.error
                ),
                "schema": ComponentHealth(
                    status=schema_health.status,
                    error=schema_health.error
                )
            }
            
            # Determine overall status
            overall_status = "ok"
            for comp in components.values():
                if comp.status == "error":
                    overall_status = "error"
                    break
                
            return ServiceHealth(
                status=overall_status,
                service=self._service_name,
                version=self._version,
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
                service=self._service_name,
                version=self._version,
                is_running=False,
                uptime=0.0,
                error=error_msg,
                components={
                    "pattern": ComponentHealth(status="error", error=str(e)),
                    "parameter": ComponentHealth(status="error", error=str(e)),
                    "sequence": ComponentHealth(status="error", error=str(e)),
                    "schema": ComponentHealth(status="error", error=str(e))
                }
            )

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0
