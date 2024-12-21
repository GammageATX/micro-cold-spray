"""Communication service for hardware control."""

from typing import Dict, Any, Optional
import os
import yaml
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.communication.clients import create_client, CommunicationClient
from micro_cold_spray.api.communication.clients.mock import MockClient
from micro_cold_spray.api.communication.services.tag_cache import TagCacheService
from micro_cold_spray.api.communication.services.motion import MotionService
from micro_cold_spray.api.communication.services.equipment import EquipmentService


class CommunicationService:
    """Service for managing hardware communication."""

    def __init__(self):
        """Initialize communication service."""
        self._service_name = "communication"
        self._client: Optional[CommunicationClient] = None
        self._tag_cache: Optional[TagCacheService] = None
        self._motion: Optional[MotionService] = None
        self._equipment: Optional[EquipmentService] = None
        self._is_running = False
        logger.info("CommunicationService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    @property
    def tag_cache(self) -> TagCacheService:
        """Get tag cache service."""
        if not self._tag_cache:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Tag cache service not initialized"
            )
        return self._tag_cache

    @property
    def motion(self) -> MotionService:
        """Get motion service."""
        if not self._motion:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Motion service not initialized"
            )
        return self._motion

    @property
    def equipment(self) -> EquipmentService:
        """Get equipment service."""
        if not self._equipment:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Equipment service not initialized"
            )
        return self._equipment

    async def _populate_mock_tags(self) -> None:
        """Populate tag cache with mock tags if using mock client."""
        if not isinstance(self._client, MockClient):
            return
            
        # Get mock tags from client
        mock_tags = self._client._tag_values
        if not mock_tags:
            return
            
        # Write mock tags to cache
        for tag_id, value in mock_tags.items():
            await self._tag_cache.write_tag(tag_id, value)
        logger.info(f"Populated tag cache with {len(mock_tags)} mock tags")

    async def start(self) -> None:
        """Start communication service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Load local config first
            config = await self._load_local_config()
            
            # Create and start client
            client_type = config.get("client_type", "mock")
            client_config = config.get("client_config", {})
            self._client = create_client(client_type, client_config)
            await self._client.start()
            
            # Initialize services
            self._tag_cache = TagCacheService()
            await self._tag_cache.start()
            
            # Populate mock tags if using mock client
            await self._populate_mock_tags()
            
            self._motion = MotionService()
            await self._motion.start()
            
            self._equipment = EquipmentService()
            await self._equipment.start()
            
            self._is_running = True
            logger.info(f"Started communication service with {client_type} client")
            
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
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service not running"
                )

            # Stop all services
            if self._equipment:
                await self._equipment.stop()
                self._equipment = None
                
            if self._motion:
                await self._motion.stop()
                self._motion = None
                
            if self._tag_cache:
                await self._tag_cache.stop()
                self._tag_cache = None

            if self._client:
                await self._client.stop()
                self._client = None
            
            self._is_running = False
            logger.info("Stopped communication service")
            
        except Exception as e:
            error_msg = f"Failed to stop communication service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def _load_local_config(self) -> Dict[str, Any]:
        """Load local communication configuration.
        
        Returns:
            Dict[str, Any]: Communication configuration
            
        Raises:
            HTTPException: If configuration loading fails
        """
        try:
            # Get config path
            config_path = os.path.join(os.getcwd(), "config", "communication.yaml")
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Communication config file not found at {config_path}")
            
            # Read config file
            with open(config_path, "r") as f:
                config_data = f.read()
            
            # Parse YAML content
            config = yaml.safe_load(config_data)
            
            # Validate config structure
            if not isinstance(config, dict):
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message="Invalid communication configuration: not a dict"
                )
            
            return config.get("communication", {})
            
        except FileNotFoundError as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=str(e)
            )
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to load communication configuration: {str(e)}"
            )

    async def check_connection(self) -> bool:
        """Check if hardware connection is healthy."""
        try:
            if not self._client:
                return False
            return await self._client.check_connection()
        except Exception as e:
            logger.warning(f"Connection check failed: {e}")
            return False

    async def health(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            is_healthy = await self.check_connection()
            
            # Check all service healths
            tag_cache_health = await self._tag_cache.health() if self._tag_cache else None
            motion_health = await self._motion.health() if self._motion else None
            equipment_health = await self._equipment.health() if self._equipment else None
            
            return {
                "status": "ok" if is_healthy else "error",
                "service": self._service_name,
                "running": self.is_running,
                "client": {
                    "initialized": self._client is not None,
                    "connected": is_healthy
                },
                "services": {
                    "tag_cache": tag_cache_health,
                    "motion": motion_health,
                    "equipment": equipment_health
                }
            }
        except Exception as e:
            error_msg = f"Failed to check health: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "service": self._service_name,
                "error": error_msg
            }
