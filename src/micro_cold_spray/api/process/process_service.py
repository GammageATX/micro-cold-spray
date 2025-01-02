"""Process service implementation."""

from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
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
