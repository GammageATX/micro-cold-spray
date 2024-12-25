"""Communication service for hardware control."""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from fastapi import status

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.communication.services.tag_mapping import TagMappingService
from micro_cold_spray.api.communication.services.tag_cache import TagCacheService
from micro_cold_spray.api.communication.services.equipment import EquipmentService
from micro_cold_spray.api.communication.services.motion import MotionService
from micro_cold_spray.api.communication.clients.factory import create_client


class CommunicationService:
    """Service for managing hardware communication."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize communication service.
        
        Args:
            config: Service configuration
        """
        self._config = config
        self._is_running = False
        self._start_time = None
        
        # Initialize services
        self._tag_mapping = TagMappingService(config)
        
        # Create client based on force_mock setting
        client_type = "mock" if config["communication"]["hardware"]["network"].get("force_mock", False) else "plc"
        client = create_client(client_type=client_type, config=config)
        
        # Initialize tag cache with client
        self._tag_cache = TagCacheService(
            client=client,
            tag_mapping=self._tag_mapping,
            poll_interval=config["communication"]["services"]["tag_cache"]["poll_rate"] / 1000.0  # Convert ms to seconds
        )
        
        self._equipment = EquipmentService(config)
        self._motion = MotionService(config)
        
        # Set tag cache for services that need it
        self._equipment.set_tag_cache(self._tag_cache)
        self._motion.set_tag_cache(self._tag_cache)
        
        logger.info("Communication service initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    @property
    def equipment(self) -> EquipmentService:
        """Get equipment service."""
        return self._equipment

    @property
    def motion(self) -> MotionService:
        """Get motion service."""
        return self._motion

    async def initialize(self) -> None:
        """Initialize communication service.
        
        Raises:
            HTTPException: If initialization fails
        """
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Initialize in order
            logger.info("Initializing tag mapping service...")
            await self._tag_mapping.initialize()
            logger.info("Tag mapping service initialized")

            logger.info("Initializing tag cache service...")
            await self._tag_cache.initialize()
            logger.info("Tag cache service initialized")

            logger.info("Initializing equipment service...")
            await self._equipment.initialize()
            logger.info("Equipment service initialized")

            logger.info("Initializing motion service...")
            await self._motion.initialize()
            logger.info("Motion service initialized")
            
            self._is_running = True
            self._start_time = datetime.now()
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
            if not self.is_running:
                await self.initialize()
            
            # Start services in order
            logger.info("Starting tag mapping service...")
            await self._tag_mapping.start()
            logger.info("Tag mapping service started")

            logger.info("Starting tag cache service...")
            await self._tag_cache.start()
            logger.info("Tag cache service started")

            logger.info("Starting equipment service...")
            await self._equipment.start()
            logger.info("Equipment service started")

            logger.info("Starting motion service...")
            await self._motion.start()
            logger.info("Motion service started")
            
            logger.info("Communication service started")
            
        except Exception as e:
            error_msg = f"Failed to start communication service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop communication service."""
        try:
            logger.info("Stopping communication service...")
            
            # Stop in reverse order
            await self._motion.stop()
            await self._equipment.stop()
            await self._tag_cache.stop()
            await self._tag_mapping.stop()
            
            self._is_running = False
            self._start_time = None
            logger.info("Communication service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping communication service: {str(e)}")
            # Don't raise during shutdown

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Health status dictionary
        """
        try:
            services_running = all([
                self._tag_mapping.is_running,
                self._tag_cache.is_running,
                self._equipment.is_running,
                self._motion.is_running
            ])
            
            uptime = None
            if self._start_time:
                uptime = (datetime.now() - self._start_time).total_seconds()
            
            return {
                "status": "ok" if services_running else "error",
                "service_name": "communication",
                "version": "1.0.0",
                "is_running": services_running,
                "uptime": uptime,
                "error": None if services_running else "One or more services not running",
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            error_msg = f"Failed to get health status: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )
