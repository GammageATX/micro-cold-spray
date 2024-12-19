"""Communication service for hardware control."""

from typing import Dict, Any, Optional
from loguru import logger

from ..base import ConfigurableService
from ..base.exceptions import ServiceError, ValidationError
from ..config import ConfigService
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
            
        except (ServiceError, ValidationError):
            raise
        except Exception as e:
            error_msg = f"Failed to start communication service: {str(e)}"
            logger.error(error_msg)
            raise ServiceError(error_msg)

    async def _load_config_and_init_clients(self) -> None:
        """Load config and initialize hardware clients."""
        # Load hardware config
        config_data = await self._config_service.get_config("hardware")
        if not config_data or not config_data.data:
            raise ValidationError("Hardware configuration is empty")
        
        config = config_data.data
        network_config = config.get("network", {})
        plc_config = network_config.get("plc", {})
        ssh_config = network_config.get("ssh", {})
        
        # Initialize PLC client
        self._plc_client = await self._init_plc_client(plc_config)
        
        # Initialize SSH client
        self._ssh_client = await self._init_ssh_client(ssh_config)

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
            # Initialize services
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
            logger.debug("Initializing tag cache service...")
            self._tag_cache = TagCacheService(self._config_service)
            logger.debug("Initializing tag mapping service...")
            self._tag_mapping = TagMappingService(self._config_service)
            
            # Start all services
            logger.debug("Starting services...")
            await self._equipment.start()
            await self._feeder.start()
            await self._motion.start()
            logger.debug("Starting tag cache service...")
            await self._tag_cache.start()
            logger.debug("Starting tag mapping service...")
            await self._tag_mapping.start()
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
            ServiceError: If health check fails
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
            services_status = {
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
            
            for component, is_healthy in services_status.items():
                if not is_healthy and component not in details:
                    details[component] = "Component not initialized or not running"
            
            # Determine overall status
            is_healthy = all(services_status.values())
            
            return {
                "status": "ok" if is_healthy else "error",
                "service_info": {
                    "name": self._service_name,
                    "version": self.version,
                    "running": self.is_running and is_healthy,
                    "uptime": str(self.uptime)
                },
                "components": services_status,
                "details": details if details else None
            }
            
        except Exception as e:
            error_msg = f"Failed to check communication service health: {str(e)}"
            logger.error(error_msg)
            raise ServiceError(error_msg)

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
            raise RuntimeError("Tag cache service not initialized")
        return self._tag_cache

    @property
    def tag_mapping(self) -> TagMappingService:
        """Get tag mapping service."""
        if not self._tag_mapping:
            raise RuntimeError("Tag mapping service not initialized")
        return self._tag_mapping
