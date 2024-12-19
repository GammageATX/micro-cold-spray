"""Communication service for hardware control."""

from typing import Dict, Any, Optional
from loguru import logger

from micro_cold_spray.core.base.services.configurable_service import ConfigurableService
from micro_cold_spray.core.errors.exceptions import CommunicationError
from micro_cold_spray.core.config import ConfigService
from micro_cold_spray.core.communication.clients import (
    PLCClient, SSHClient
)
from micro_cold_spray.core.communication.services.equipment import EquipmentService
from micro_cold_spray.core.communication.services.feeder import FeederService
from micro_cold_spray.core.communication.services.motion import MotionService
from micro_cold_spray.core.communication.services.tag_cache import TagCacheService
from micro_cold_spray.core.communication.services.tag_mapping import TagMappingService


class CommunicationService(ConfigurableService):
    """Service for hardware communication and control."""

    def __init__(self, config_service: ConfigService):
        """Initialize communication service.
        
        Args:
            config_service: Configuration service instance
        """
        super().__init__(service_name="communication", config_service=config_service)
        
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
            await self._load_config_and_init_clients()
            await self._init_and_start_services()
            logger.info("Communication service started")
            
        except (CommunicationError, ValidationError):
            raise
        except Exception as e:
            error_msg = f"Failed to start communication service: {str(e)}"
            logger.error(error_msg)
            raise CommunicationError(error_msg)

    async def _load_config_and_init_clients(self) -> None:
        """Load config and initialize hardware clients."""
        try:
            # Load network configuration
            network_config = await self._get_communication_config('network')
            if not network_config:
                raise ValidationError("Network configuration is empty")
            
            plc_config = network_config.get("plc", {})
            ssh_config = network_config.get("ssh", {})
            
            # Initialize PLC client
            self._plc_client = await self._init_plc_client(plc_config)
            
            # Initialize SSH client
            self._ssh_client = await self._init_ssh_client(ssh_config)
            
        except Exception as e:
            logger.error(f"Failed to load config and initialize clients: {e}")
            raise CommunicationError(
                "Failed to initialize communication clients",
                {"error": str(e)}
            )

    async def _init_plc_client(self, plc_config: Dict[str, Any]) -> PLCClient:
        """Initialize PLC client with fallback to mock."""
        try:
            client = create_plc_client(plc_config)
            await client.connect()
            return client
        except Exception as e:
            logger.warning(f"Failed to connect to PLC, using mock client: {e}")
            return create_plc_client({}, use_mock=True)

    async def _init_ssh_client(self, ssh_config: Dict[str, Any]) -> SSHClient:
        """Initialize SSH client with fallback to mock."""
        try:
            client = create_ssh_client(ssh_config)
            await client.connect()
            return client
        except Exception as e:
            logger.warning(f"Failed to connect to SSH, using mock client: {e}")
            return create_ssh_client({}, use_mock=True)

    async def _init_and_start_services(self) -> None:
        """Initialize and start all services."""
        try:
            logger.debug("Initializing services...")
            
            # Initialize tag mapping first
            logger.debug("Initializing tag mapping service...")
            self._tag_mapping = TagMappingService(self._config_service)
            await self._tag_mapping.start()
            
            # Initialize tag cache with clients
            logger.debug("Initializing tag cache service...")
            self._tag_cache = TagCacheService(
                config_service=self._config_service,
                plc_client=self._plc_client,
                ssh_client=self._ssh_client,
                polling_interval=0.1  # 100ms default polling
            )
            await self._tag_cache.start()
            
            # Initialize control services
            self._equipment = EquipmentService(
                plc_client=self._plc_client,
                config_service=self._config_service
            )
            self._feeder = FeederService(
                ssh_client=self._ssh_client,
                config_service=self._config_service
            )
            self._motion = MotionService(
                plc_client=self._plc_client,
                config_service=self._config_service
            )
            
            # Start control services
            logger.debug("Starting control services...")
            await self._equipment.start()
            await self._feeder.start()
            await self._motion.start()
            logger.debug("All services started")
            
        except Exception as e:
            logger.error(f"Failed to initialize and start services: {e}")
            raise

    async def _stop(self) -> None:
        """Stop communication service."""
        await self._cleanup()
        logger.info("Communication service stopped")

    async def _cleanup(self) -> None:
        """Clean up resources."""
        # Stop services in reverse order
        if self._motion:
            await self._motion.stop()
        if self._feeder:
            await self._feeder.stop()
        if self._equipment:
            await self._equipment.stop()
        if self._tag_cache:
            await self._tag_cache.stop()
        if self._tag_mapping:
            await self._tag_mapping.stop()
            
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
            CommunicationError: If health check fails
        """
        try:
            logger.debug("Checking communication service health")
            
            # Check clients first
            plc_status = False
            ssh_status = False
            plc_error = None
            ssh_error = None
            
            try:
                plc_status = await self._plc_client.check_connection()
                logger.debug(f"PLC client status: {plc_status}")
            except Exception as e:
                logger.error(f"PLC client health check failed: {e}")
                plc_error = str(e)
                
            try:
                ssh_status = await self._ssh_client.check_connection()
                logger.debug(f"SSH client status: {ssh_status}")
            except Exception as e:
                logger.error(f"SSH client health check failed: {e}")
                ssh_error = str(e)
            
            # Check services
            status = {
                "plc": plc_status,
                "ssh": ssh_status,
                "equipment": self._equipment and self._equipment.is_running,
                "feeder": self._feeder and self._feeder.is_running,
                "motion": self._motion and self._motion.is_running,
                "tag_cache": self._tag_cache and self._tag_cache.is_running,
                "tag_mapping": self._tag_mapping and self._tag_mapping.is_running
            }
            
            # Add error details if available
            details = {}
            if plc_error:
                details["plc"] = plc_error
            if ssh_error:
                details["ssh"] = ssh_error
            
            for component, is_healthy in status.items():
                if not is_healthy and component not in details:
                    details[component] = "Component not initialized or not running"
            
            # If any component is unhealthy, raise an error
            if not all(status.values()):
                error_msg = "Communication service health check failed: "
                error_msg += ", ".join(f"{k}: {v}" for k, v in details.items())
                raise CommunicationError(error_msg)
            
            logger.debug("All components healthy")
            return {
                "status": "healthy",
                "components": status
            }
            
        except CommunicationError:
            raise
        except Exception as e:
            error_msg = f"Failed to check communication service health: {str(e)}"
            logger.error(error_msg)
            raise CommunicationError(error_msg)

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
