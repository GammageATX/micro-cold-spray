"""Format service implementation."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth


class FormatService:
    """Format service."""

    def __init__(self, enabled_formats: List[str], version: str = "1.0.0"):
        """Initialize service."""
        self._service_name = "format"
        self._version = version
        self._is_running = False
        self._start_time = None
        
        # Initialize components to None
        self._enabled_formats = None
        self._formatters = None
        self._failed_formatters = {}  # Track failed formatters
        
        # Store constructor args for initialization
        self._init_enabled_formats = enabled_formats
        
        logger.info(f"{self.service_name} service initialized")

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
            
            # Initialize enabled formats
            self._enabled_formats = self._init_enabled_formats
            
            # Initialize formatters
            self._formatters = {}
            await self._load_formatters()
            
            logger.info(f"Enabled formats: {', '.join(self._enabled_formats)}")
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def _load_formatters(self) -> None:
        """Load formatters for enabled formats."""
        for fmt in self._enabled_formats:
            try:
                self._formatters[fmt] = {}  # Initialize formatter
                # If formatter was previously failed, remove from failed list
                self._failed_formatters.pop(fmt, None)
            except Exception as e:
                logger.error(f"Failed to load formatter {fmt}: {e}")
                self._failed_formatters[fmt] = str(e)

    async def _attempt_recovery(self) -> None:
        """Attempt to recover failed formatters."""
        if self._failed_formatters:
            logger.info(f"Attempting to recover {len(self._failed_formatters)} failed formatters...")
            await self._load_formatters()

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )

            if not self._enabled_formats or not self._formatters:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"{self.service_name} service not initialized"
                )
            
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
            # Attempt recovery of failed formatters
            await self._attempt_recovery()
            
            # Check component health
            components = {}
            formatters_loaded = False
            
            for fmt in self._enabled_formats or []:
                is_loaded = fmt in self._formatters
                formatters_loaded = formatters_loaded or is_loaded
                components[fmt] = ComponentHealth(
                    status="ok" if is_loaded else "error",
                    error=None if is_loaded else f"Formatter not loaded for {fmt}"
                )
            
            # Add failed formatters component if any exist
            if self._failed_formatters:
                failed_list = ", ".join(self._failed_formatters.keys())
                components["failed_formatters"] = ComponentHealth(
                    status="error",
                    error=f"Failed formatters: {failed_list}"
                )
            
            # Overall status is error only if no formatters loaded
            overall_status = "error" if not formatters_loaded else "ok"
            
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
                            for name in self._enabled_formats or []}
            )
