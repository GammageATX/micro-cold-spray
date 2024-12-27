"""Communication service implementation."""

from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
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
        self._service_name = "communication"
        self._config = config
        self._version = config.get("version", "1.0.0")
        self._is_running = False
        self._mode = config.get("mode", "mock")
        self._start_time = None
        
        # Initialize services to None
        self._tag_mapping = None
        self._tag_cache = None
        self._equipment = None
        self._motion = None
        
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
        """Get service uptime."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            logger.info(f"Initializing {self.service_name} service...")
            
            # Create services in dependency order
            self._tag_mapping = TagMappingService(self._config)  # No dependencies
            
            # Initialize clients based on mode
            mode = self._config.get("mode", "mock")
            if mode == "mock":
                plc_client = MockPLCClient(self._config)
                ssh_client = None
            else:
                plc_client = PLCClient(self._config)
                ssh_client = SSHClient(self._config)
            
            # Create remaining services in dependency order
            self._tag_cache = TagCacheService(plc_client, ssh_client, self._tag_mapping)  # Depends on tag_mapping
            self._equipment = EquipmentService(self._config)  # Depends on tag_cache
            self._motion = MotionService(self._config)  # Depends on tag_cache
            
            # Initialize services in dependency order
            await self._tag_mapping.initialize()
            await self._tag_cache.initialize()
            await self._equipment.initialize()
            await self._motion.initialize()
            
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start service and all components."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            if not all([self._tag_mapping, self._tag_cache, self._equipment, self._motion]):
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"{self.service_name} service not initialized"
                )
            
            logger.info(f"Starting {self.service_name} service...")
            
            # Start services in dependency order
            await self._tag_mapping.start()
            await self._tag_cache.start()
            
            # Set tag cache dependencies
            self._equipment.set_tag_cache(self._tag_cache)
            self._motion.set_tag_cache(self._tag_cache)
            
            # Start remaining services
            await self._equipment.start()
            await self._motion.start()
            
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
        """Stop service and all components."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service not running"
                )
            
            # 1. Stop services in reverse dependency order
            await self._motion.stop()
            await self._equipment.stop()
            await self._tag_cache.stop()
            await self._tag_mapping.stop()
            
            # 2. Clear service references
            self._motion = None
            self._equipment = None
            self._tag_cache = None
            self._tag_mapping = None
            
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
            # Get health from components
            tag_mapping_health = await self._tag_mapping.health() if self._tag_mapping else None
            tag_cache_health = await self._tag_cache.health() if self._tag_cache else None
            equipment_health = await self._equipment.health() if self._equipment else None
            motion_health = await self._motion.health() if self._motion else None
            
            # Build component statuses
            components = {
                "tag_mapping": ComponentHealth(
                    status="ok" if tag_mapping_health and tag_mapping_health.status == "ok" else "error",
                    error=tag_mapping_health.error if tag_mapping_health else "Component not initialized"
                ),
                "tag_cache": ComponentHealth(
                    status="ok" if tag_cache_health and tag_cache_health.status == "ok" else "error",
                    error=tag_cache_health.error if tag_cache_health else "Component not initialized"
                ),
                "equipment": ComponentHealth(
                    status="ok" if equipment_health and equipment_health.status == "ok" else "error",
                    error=equipment_health.error if equipment_health else "Component not initialized"
                ),
                "motion": ComponentHealth(
                    status="ok" if motion_health and motion_health.status == "ok" else "error",
                    error=motion_health.error if motion_health else "Component not initialized"
                )
            }
            
            # Overall status is error if any component is in error
            overall_status = "error" if any(c.status == "error" for c in components.values()) else "ok"
            
            return ServiceHealth(
                status=overall_status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if overall_status == "ok" else "One or more components in error state",
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
                            for name in ["tag_mapping", "tag_cache", "equipment", "motion"]}
            )
