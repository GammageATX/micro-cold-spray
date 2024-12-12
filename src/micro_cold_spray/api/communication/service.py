"""Communication service for hardware control."""

from typing import Dict, Any, Optional
from loguru import logger

from ..base import ConfigurableService
from ..config import ConfigService
from .exceptions import HardwareError
from .clients import (
    create_plc_client,
    create_ssh_client,
    PLCClient,
    SSHClient
)
from .services import (
    EquipmentService,
    FeederService,
    MotionService,
    TagCacheService,
    TagMappingService
)


class CommunicationService(ConfigurableService):
    """Service for hardware communication and control."""

    def __init__(self):
        super().__init__(service_name="communication")
        self._config_service = ConfigService()
        
        # Clients
        self._plc_client: Optional[PLCClient] = None
        self._ssh_client: Optional[SSHClient] = None
        
        # Services
        self._equipment: Optional[EquipmentService] = None
        self._feeder: Optional[FeederService] = None
        self._motion: Optional[MotionService] = None
        self._tag_cache: Optional[TagCacheService] = None
        self._tag_mapping: Optional[TagMappingService] = None

    async def _start(self) -> None:
        """Start communication service."""
        try:
            # Load hardware config
            config = await self._config_service.get_config("hardware")
            await self.configure(config)
            
            # Initialize with config
            plc_config = config.get("network", {}).get("plc", {})
            ssh_config = config.get("network", {}).get("ssh", {})
            
            try:
                self._plc_client = create_plc_client(plc_config)
            except Exception as e:
                raise HardwareError(f"Failed to create PLC client: {str(e)}", device="plc")
                
            try:
                self._ssh_client = create_ssh_client(ssh_config)
            except Exception as e:
                raise HardwareError(f"Failed to create SSH client: {str(e)}", device="ssh")
            
            # Initialize services
            try:
                self._equipment = EquipmentService(
                    plc_client=self._plc_client,
                    ssh_client=self._ssh_client,
                    config=config.get("physical", {})
                )
                
                self._feeder = FeederService(
                    plc_client=self._plc_client,
                    ssh_client=self._ssh_client,
                    config=config.get("physical", {}).get("hardware_sets", {})
                )
                
                self._motion = MotionService(
                    plc_client=self._plc_client,
                    config=config.get("physical", {}).get("stage", {})
                )
                
                self._tag_cache = TagCacheService(
                    plc_client=self._plc_client,
                    config=config.get("network", {}).get("plc", {})
                )
                
                self._tag_mapping = TagMappingService(
                    plc_client=self._plc_client,
                    config=config.get("network", {}).get("plc", {})
                )
            except Exception as e:
                raise HardwareError(f"Failed to initialize services: {str(e)}", device="services")
            
            # Start all services
            try:
                await self._equipment.start()
                await self._feeder.start()
                await self._motion.start()
                await self._tag_cache.start()
                await self._tag_mapping.start()
            except Exception as e:
                raise HardwareError(f"Failed to start services: {str(e)}", device="services")
            
            logger.info("Communication service started")
            
        except HardwareError:
            raise
        except Exception as e:
            error_msg = f"Failed to start communication service: {str(e)}"
            logger.error(error_msg)
            raise HardwareError(error_msg, device="unknown")

    async def _stop(self) -> None:
        """Stop communication service."""
        await self._cleanup()
        logger.info("Communication service stopped")

    async def _cleanup(self) -> None:
        """Clean up resources."""
        # Stop services
        if self._tag_mapping:
            await self._tag_mapping.stop()
        if self._tag_cache:
            await self._tag_cache.stop()
        if self._motion:
            await self._motion.stop()
        if self._feeder:
            await self._feeder.stop()
        if self._equipment:
            await self._equipment.stop()
            
        # Stop clients
        if self._ssh_client:
            await self._ssh_client.stop()
        if self._plc_client:
            await self._plc_client.stop()

    async def check_health(self) -> Dict[str, Any]:
        """Check service health.
        
        Returns:
            Health status dictionary
            
        Raises:
            HardwareError: If health check fails
        """
        try:
            status = {
                "plc": await self._plc_client.check_connection(),
                "ssh": await self._ssh_client.check_connection(),
                "equipment": self._equipment.is_running,
                "feeder": self._feeder.is_running,
                "motion": self._motion.is_running,
                "tag_cache": self._tag_cache.is_running,
                "tag_mapping": self._tag_mapping.is_running
            }
            
            return {
                "status": "healthy" if all(status.values()) else "degraded",
                "components": status
            }
            
        except Exception as e:
            raise HardwareError(
                "Failed to check communication health",
                "communication",
                {"error": str(e)}
            )

    @property
    def equipment(self) -> EquipmentService:
        """Get equipment service."""
        if not self._equipment:
            raise RuntimeError("Equipment service not initialized")
        return self._equipment

    @property
    def feeder(self) -> FeederService:
        """Get feeder service."""
        if not self._feeder:
            raise RuntimeError("Feeder service not initialized")
        return self._feeder

    @property
    def motion(self) -> MotionService:
        """Get motion service."""
        if not self._motion:
            raise RuntimeError("Motion service not initialized")
        return self._motion

    @property
    def tag_cache(self) -> TagCacheService:
        """Get tag cache service."""
        if not self._tag_cache:
            raise RuntimeError("Tag cache not initialized")
        return self._tag_cache

    @property
    def tag_mapping(self) -> TagMappingService:
        """Get tag mapping service."""
        if not self._tag_mapping:
            raise RuntimeError("Tag mapping not initialized")
        return self._tag_mapping
