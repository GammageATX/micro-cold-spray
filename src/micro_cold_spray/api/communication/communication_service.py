"""Communication service implementation."""

from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import get_uptime, ServiceHealth, ComponentHealth


from micro_cold_spray.api.communication.services import (
    EquipmentService,
    MotionService,
    TagCacheService,
    TagMappingService
)
from micro_cold_spray.api.communication.clients import (
    MockPLCClient,
    PLCClient,
    SSHClient
)


class CommunicationService:
    """Communication service."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize service.
        
        Args:
            config: Service configuration
        """
        self._config = config
        self._version = config.get("version", "1.0.0")
        self._is_running = False
        self._mode = config.get("mode", "mock")
        self._start_time = None
        
        # Initialize services
        self._tag_mapping = TagMappingService(config)
        self._tag_cache = None  # Initialized in start()
        self._equipment = EquipmentService(config)
        self._motion = MotionService(config)
        
        logger.info("Communication service initialized")

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            logger.info("Initializing communication service...")
            
            # Initialize tag mapping service
            await self._tag_mapping.initialize()
            
            # Initialize equipment service
            await self._equipment.initialize()
            
            # Initialize motion service
            await self._motion.initialize()
            
            logger.info("Communication service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize communication service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start service and all components."""
        try:
            logger.info("Starting communication service...")
            
            # Start tag mapping service
            await self._tag_mapping.start()
            
            # Initialize clients based on mode
            mode = self._config.get("mode", "mock")
            if mode == "mock":
                plc_client = MockPLCClient(self._config)
                ssh_client = None
            else:
                plc_client = PLCClient(self._config)
                ssh_client = SSHClient(self._config)
            
            # Initialize and start tag cache service
            self._tag_cache = TagCacheService(plc_client, ssh_client, self._tag_mapping)
            await self._tag_cache.initialize()
            await self._tag_cache.start()
            
            # Set tag cache and start equipment service
            self._equipment.set_tag_cache(self._tag_cache)
            await self._equipment.start()
            
            # Set tag cache and start motion service
            self._motion.set_tag_cache(self._tag_cache)
            await self._motion.start()
            
            self._is_running = True
            self._start_time = datetime.now()
            logger.info("Communication service started successfully")
            
        except Exception as e:
            self._is_running = False
            error_msg = f"Failed to start communication service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop service and all components."""
        try:
            # Stop services in reverse order
            await self._motion.stop()
            await self._equipment.stop()
            if self._tag_cache:
                await self._tag_cache.stop()
            await self._tag_mapping.stop()
            
            self._is_running = False
            logger.info("Communication service stopped")
            
        except Exception as e:
            error_msg = f"Error during communication service shutdown: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

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
        """Get service uptime."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    async def health(self) -> ServiceHealth:
        """Get service health status."""
        try:
            components = {
                "tag_mapping": ComponentHealth(
                    status="ok" if self._tag_mapping.is_running else "error",
                    error=None if self._tag_mapping.is_running else "Not running"
                ),
                "tag_cache": ComponentHealth(
                    status="ok" if self._tag_cache and self._tag_cache.is_running else "error",
                    error=None if self._tag_cache and self._tag_cache.is_running else "Not running"
                ),
                "equipment": ComponentHealth(
                    status="ok" if self._equipment.is_running else "error",
                    error=None if self._equipment.is_running else "Not running"
                ),
                "motion": ComponentHealth(
                    status="ok" if self._motion.is_running else "error",
                    error=None if self._motion.is_running else "Not running"
                )
            }
            
            return ServiceHealth(
                status="ok" if self.is_running else "error",
                service="communication",
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if self.is_running else "Service not running",
                mode=self._mode,
                components=components
            )
            
        except Exception as e:
            error_msg = f"Failed to get communication service health: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service="communication",
                version=self.version,
                is_running=False,
                uptime=self.uptime,
                error=error_msg,
                mode=self._mode,
                components={
                    "tag_mapping": ComponentHealth(status="error", error=error_msg),
                    "tag_cache": ComponentHealth(status="error", error=error_msg),
                    "equipment": ComponentHealth(status="error", error=error_msg),
                    "motion": ComponentHealth(status="error", error=error_msg)
                }
            )
