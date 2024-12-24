"""Communication service for hardware control."""

from typing import Dict, Any, Optional, List, Set
import os
import yaml
from fastapi import status
from loguru import logger
from datetime import datetime
import asyncio
import time

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.communication.clients import create_client, CommunicationClient
from micro_cold_spray.api.communication.clients.mock import MockClient
from micro_cold_spray.api.communication.services.tag_cache import TagCacheService
from micro_cold_spray.api.communication.services.motion import MotionService
from micro_cold_spray.api.communication.services.equipment import EquipmentService
from micro_cold_spray.api.communication.services.tag_mapping import TagMappingService
from micro_cold_spray.api.communication.models.tags import TagValue, TagMetadata
from micro_cold_spray.utils import get_uptime


class CommunicationService:
    """Service for managing hardware communication."""

    def __init__(self):
        """Initialize communication service."""
        self._service_name = "communication"
        self._version = "1.0.0"
        self._start_time = None
        self._client: Optional[CommunicationClient] = None
        self._tag_cache = TagCacheService()
        self._tag_mapping = TagMappingService()
        self._motion = MotionService()
        self._equipment = EquipmentService()
        self._is_running = False
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

    async def start(self) -> None:
        """Start communication service and all sub-services."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Start sub-services
            await self._tag_cache.start()
            await self._tag_mapping.start()
            await self._motion.start()
            await self._equipment.start()

            # Initialize hardware client
            config_path = os.getenv("HARDWARE_CONFIG", "config/hardware.yaml")
            if os.path.exists(config_path):
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                client_type = config.get("client_type", "mock")
                self._client = create_client(client_type, config)
                await self._client.connect()
            else:
                logger.warning(f"No hardware config found at {config_path}, using mock client")
                self._client = MockClient({})

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
        """Stop communication service and all sub-services."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service not running"
                )

            # Stop sub-services
            await self._tag_cache.stop()
            await self._tag_mapping.stop()
            await self._motion.stop()
            await self._equipment.stop()

            # Disconnect hardware client
            if self._client:
                await self._client.disconnect()
                self._client = None

            self._is_running = False
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
            Health status dictionary
        """
        uptime = time.time() - self._start_time.timestamp() if self._start_time else 0
        
        return {
            "status": "ok" if self.is_running else "error",
            "service": self._service_name,
            "version": self._version,
            "running": self.is_running,
            "uptime": uptime,
            "client": {
                "type": self._client.__class__.__name__ if self._client else None,
                "connected": self._client.is_connected if self._client else False
            },
            "sub_services": {
                "tag_cache": await self._tag_cache.health(),
                "tag_mapping": await self._tag_mapping.health(),
                "motion": await self._motion.health(),
                "equipment": await self._equipment.health()
            }
        }
