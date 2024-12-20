"""Configuration service endpoints."""

from typing import Dict, Any, List, Type
from fastapi import status

from micro_cold_spray.api.base.base_router import BaseRouter
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.models.config_models import ConfigData


class ConfigRouter(BaseRouter):
    """Configuration service router."""

    def __init__(self, service: ConfigService):
        """Initialize router.
        
        Args:
            service: Configuration service instance
        """
        super().__init__(prefix="/config")
        self.service = service
        self.services = [service]  # For health checks

        # Register routes
        self.add_api_route("/types", self.get_config_types, methods=["GET"])
        self.add_api_route("/types/{type_name}", self.get_config_type, methods=["GET"])
        self.add_api_route("/types/{type_name}", self.register_config_type, methods=["POST"])
        self.add_api_route("/configs", self.get_configs, methods=["GET"])
        self.add_api_route("/configs/{config_type}", self.get_config, methods=["GET"])
        self.add_api_route("/configs/{config_type}", self.update_config, methods=["PUT"])
        self.add_api_route("/configs/{config_type}", self.delete_config, methods=["DELETE"])

    async def get_config_types(self) -> Dict[str, Type[ConfigData]]:
        """Get registered configuration types."""
        try:
            return await self.service.get_config_types()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to get config types",
                context={"error": str(e)},
                cause=e
            )

    async def get_config_type(self, type_name: str) -> Type[ConfigData]:
        """Get configuration type by name."""
        try:
            return self.service.get_config_type(type_name)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to get config type {type_name}",
                context={"type": type_name, "error": str(e)},
                cause=e
            )

    async def register_config_type(self, type_name: str, config_type: Type[ConfigData]) -> None:
        """Register configuration type."""
        try:
            self.service.register_config_type(config_type)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to register config type {type_name}",
                context={"type": type_name, "error": str(e)},
                cause=e
            )

    async def get_configs(self) -> List[ConfigData]:
        """Get all configurations."""
        try:
            return await self.service.get_configs()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to get configs",
                context={"error": str(e)},
                cause=e
            )

    async def get_config(self, config_type: str) -> ConfigData:
        """Get configuration by type."""
        try:
            return await self.service.get_config(config_type)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to get config {config_type}",
                context={"type": config_type, "error": str(e)},
                cause=e
            )

    async def update_config(self, config_type: str, config: ConfigData) -> None:
        """Update configuration."""
        try:
            await self.service.update_config(config)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to update config {config_type}",
                context={"type": config_type, "error": str(e)},
                cause=e
            )

    async def delete_config(self, config_type: str) -> None:
        """Delete configuration."""
        try:
            await self.service.delete_config(config_type)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to delete config {config_type}",
                context={"type": config_type, "error": str(e)},
                cause=e
            )
