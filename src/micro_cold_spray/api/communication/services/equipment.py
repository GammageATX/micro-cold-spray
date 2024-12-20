"""Equipment control service implementation."""

from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config import ConfigService
from micro_cold_spray.api.communication.clients.base import BaseClient


class EquipmentService(ConfigurableService):
    """Service for controlling equipment state."""

    def __init__(self, config_service: ConfigService, client: BaseClient):
        """Initialize equipment service.
        
        Args:
            config_service: Configuration service instance
            client: Hardware client instance
        """
        super().__init__(service_name="equipment", config_service=config_service)
        self._client = client

    async def _start(self) -> None:
        """Initialize service."""
        try:
            logger.debug("Loading equipment configuration")
            equipment_config = await self._config_service.get_config("equipment")
            if not equipment_config:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Equipment configuration not found"
                )
                
            logger.info("Equipment service initialized")
        except Exception as e:
            logger.error(f"Failed to start equipment service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start equipment service: {e}",
                context={"error": str(e)},
                cause=e
            )

    async def _stop(self) -> None:
        """Cleanup service."""
        logger.info("Equipment service stopped")

    async def get_state(self) -> Dict[str, Any]:
        """Get current equipment state.
        
        Returns:
            Current equipment state
            
        Raises:
            HTTPException: If state cannot be retrieved
        """
        try:
            return await self._client.get_equipment_state()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to get equipment state",
                context={"error": str(e)},
                cause=e
            )

    async def set_state(self, state: Dict[str, Any]) -> None:
        """Set equipment state.
        
        Args:
            state: Desired equipment state
            
        Raises:
            HTTPException: If state cannot be set
        """
        try:
            await self._client.set_equipment_state(state)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to set equipment state",
                context={"state": state, "error": str(e)},
                cause=e
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            # Get current state
            state = await self.get_state()
            
            # Check client connection
            client_health = await self._client.check_health()
            
            return {
                "status": "ok" if client_health["status"] == "ok" else "error",
                "components": {
                    "client": client_health["status"] == "ok",
                    "state": state is not None
                },
                "details": client_health.get("details")
            }
        except Exception as e:
            error_msg = f"Failed to check equipment health: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }
