"""Communication service implementation."""

from typing import Dict, Any, Optional
from datetime import datetime
import time
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.communication.clients.plc import PLCClient
from micro_cold_spray.api.communication.clients.ssh import SSHClient
from micro_cold_spray.api.communication.clients.mock import MockPLCClient
from micro_cold_spray.api.communication.services.tag_mapping import TagMappingService
from micro_cold_spray.api.communication.services.tag_cache import TagCacheService
from micro_cold_spray.api.communication.services.equipment import EquipmentService
from micro_cold_spray.api.communication.services.motion import MotionService
from micro_cold_spray.api.communication.models.equipment import EquipmentState


class CommunicationService:
    """Service for hardware communication."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize communication service.
        
        Args:
            config: Service configuration
        """
        self._config = config
        self._service_name = "communication"
        self._version = "1.0.0"
        self._start_time = None
        self._is_running = False
        self._initialized = False
        
        # Initialize clients based on force_mock setting
        force_mock = config["communication"]["hardware"]["network"].get("force_mock", False)
        if force_mock:
            logger.info("Using mock client")
            self._plc_client = MockPLCClient(config)
            self._ssh_client = None
        else:
            logger.info("Using hardware clients")
            self._plc_client = PLCClient(config)
            self._ssh_client = SSHClient(config)
        
        # Initialize services
        self._tag_mapping = TagMappingService(config)
        self._tag_cache = TagCacheService(self._plc_client, self._ssh_client, self._tag_mapping)
        
        # Initialize equipment and motion services
        self._equipment = EquipmentService(config)
        self._equipment.set_tag_cache(self._tag_cache)
        
        self._motion = MotionService(config)
        self._motion.set_tag_cache(self._tag_cache)
        
        logger.info("CommunicationService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self._start_time.timestamp() if self._start_time else 0

    @property
    def equipment(self) -> EquipmentService:
        """Get equipment service."""
        return self._equipment

    @property
    def motion(self) -> MotionService:
        """Get motion service."""
        return self._motion

    @property
    def tag_cache(self) -> TagCacheService:
        """Get tag cache service."""
        return self._tag_cache

    async def get_state(self) -> EquipmentState:
        """Get current equipment state.
        
        Returns:
            Current equipment state
            
        Raises:
            HTTPException: If read fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            return await self._equipment.get_state()

        except Exception as e:
            error_msg = "Failed to get equipment state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def initialize(self) -> None:
        """Initialize service and all subservices.
        
        Raises:
            HTTPException: If initialization fails
        """
        try:
            if self._initialized:
                logger.debug("Communication service already initialized")
                return
                
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )
            
            # Connect clients first
            await self._plc_client.connect()
            if self._ssh_client:
                await self._ssh_client.connect()
            
            # Initialize tag mapping first
            await self._tag_mapping.initialize()
            
            # Initialize and start tag cache
            await self._tag_cache.initialize()
            await self._tag_cache.start()
            
            # Initialize equipment and motion services
            await self._equipment.initialize()
            await self._motion.initialize()
            
            self._initialized = True
            logger.info("Communication service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize communication service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start communication service.
        
        Raises:
            HTTPException: If startup fails
        """
        try:
            if self.is_running:
                logger.debug("Communication service already running")
                return
                
            if not self._initialized:
                await self.initialize()
            
            # Start services (tag cache already started in initialize)
            await self._equipment.start()
            await self._motion.start()
            
            self._start_time = datetime.now()
            self._is_running = True
            logger.info("Communication service started")
            
        except Exception as e:
            error_msg = f"Failed to start communication service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop communication service.
        
        Raises:
            HTTPException: If shutdown fails
        """
        try:
            if not self.is_running:
                return
            
            # Stop services
            await self._motion.stop()
            await self._equipment.stop()
            await self._tag_cache.stop()
            
            # Disconnect clients
            if self._ssh_client:
                await self._ssh_client.disconnect()
            await self._plc_client.disconnect()
            
            self._is_running = False
            self._initialized = False
            self._start_time = None
            logger.info("Communication service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop communication service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Dict[str, Any]: Health status dictionary
        """
        try:
            # Get health status from components
            tag_mapping_health = await self._tag_mapping.health()
            tag_cache_health = await self._tag_cache.health()
            equipment_health = await self._equipment.health()
            motion_health = await self._motion.health()
            
            # Service is healthy if all components are healthy
            is_healthy = all(h["status"] == "ok" for h in [
                tag_mapping_health,
                tag_cache_health,
                equipment_health,
                motion_health
            ])
            
            return {
                "status": "ok" if is_healthy else "error",
                "service_name": self._service_name,
                "version": self._version,
                "is_running": self.is_running,
                "uptime": self.uptime,
                "error": None,
                "components": {
                    "tag_mapping": tag_mapping_health,
                    "tag_cache": tag_cache_health,
                    "equipment": equipment_health,
                    "motion": motion_health
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Failed to get health status: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "service_name": self._service_name,
                "version": self._version,
                "is_running": False,
                "uptime": 0,
                "error": error_msg,
                "components": {},
                "timestamp": datetime.now().isoformat()
            }
