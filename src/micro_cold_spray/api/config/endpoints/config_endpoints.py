"""Configuration API endpoints."""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, status

from micro_cold_spray.api.base.base_router import BaseRouter
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.models.config_models import (
    ConfigData,
    ConfigMetadata,
    ConfigSchema,
    FormatMetadata
)


class ConfigRouter(BaseRouter):
    """Configuration API router."""

    def __init__(self, config_service: ConfigService) -> None:
        """Initialize router.
        
        Args:
            config_service: Configuration service
        """
        super().__init__()
        self._config_service = config_service
        self._router = APIRouter(prefix="/config", tags=["config"])
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up router endpoints."""
        self._router.get("/types", response_model=List[str])(self.get_config_types)
        self._router.get("/formats", response_model=Dict[str, FormatMetadata])(self.get_format_metadata)
        self._router.get("/schemas", response_model=Dict[str, ConfigSchema])(self.get_schemas)
        self._router.get("/configs", response_model=Dict[str, ConfigData])(self.get_configs)
        self._router.get("/config/{config_type}", response_model=ConfigData)(self.get_config)
        self._router.post("/config/{config_type}")(self.set_config)
        self._router.delete("/config/{config_type}")(self.delete_config)

    async def get_config_types(self) -> List[str]:
        """Get available configuration types.
        
        Returns:
            List of configuration types
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._config_service.get_config_types()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get config types",
                context={"error": str(e)},
                cause=e
            )

    async def get_format_metadata(self) -> Dict[str, FormatMetadata]:
        """Get format metadata.
        
        Returns:
            Format metadata by type
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._config_service.get_format_metadata()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get format metadata",
                context={"error": str(e)},
                cause=e
            )

    async def get_schemas(self) -> Dict[str, ConfigSchema]:
        """Get configuration schemas.
        
        Returns:
            Schemas by type
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._config_service.get_schemas()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get schemas",
                context={"error": str(e)},
                cause=e
            )

    async def get_configs(self) -> Dict[str, ConfigData]:
        """Get all configurations.
        
        Returns:
            Configurations by type
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._config_service.get_configs()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get configs",
                context={"error": str(e)},
                cause=e
            )

    async def get_config(self, config_type: str) -> ConfigData:
        """Get configuration.
        
        Args:
            config_type: Configuration type
            
        Returns:
            Configuration data
            
        Raises:
            HTTPException: If config not found (404) or service unavailable (503)
        """
        try:
            return await self._config_service.get_config(config_type)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get config",
                context={"error": str(e)},
                cause=e
            )

    async def set_config(self, config_type: str, config: Dict[str, Any]) -> None:
        """Set configuration.
        
        Args:
            config_type: Configuration type
            config: Configuration data
            
        Raises:
            HTTPException: If validation fails (422) or service unavailable (503)
        """
        try:
            await self._config_service.set_config(config_type, config)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to set config",
                context={"error": str(e)},
                cause=e
            )

    async def delete_config(self, config_type: str) -> None:
        """Delete configuration.
        
        Args:
            config_type: Configuration type
            
        Raises:
            HTTPException: If config not found (404) or service unavailable (503)
        """
        try:
            await self._config_service.delete_config(config_type)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to delete config",
                context={"error": str(e)},
                cause=e
            )

    @property
    def router(self) -> APIRouter:
        """Get router.
        
        Returns:
            FastAPI router
        """
        return self._router
