"""Schema service for configuration validation."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml

from loguru import logger

from micro_cold_spray.api.base import BaseService
from micro_cold_spray.api.base.exceptions import ConfigurationError
from micro_cold_spray.api.config.models import ConfigSchema


class SchemaService(BaseService):
    """Service for schema validation."""

    def __init__(self, schema_dir: Path):
        """Initialize schema service."""
        super().__init__(service_name="schema")
        self._schema_dir = schema_dir
        self._schema_dir.mkdir(exist_ok=True)
        self._schemas: Dict[str, ConfigSchema] = {}

    async def _start(self) -> None:
        """Start schema service."""
        try:
            self._schema_dir.mkdir(exist_ok=True)
            await self._load_schemas()
            logger.info("Schema service started with {} schemas", len(self._schemas))
        except Exception as e:
            raise ConfigurationError("Failed to start schema service", {"error": str(e)})

    async def _load_schemas(self) -> None:
        """Load all schema files."""
        try:
            for schema_file in self._schema_dir.glob("*.yaml"):
                schema_type = schema_file.stem
                with open(schema_file, 'r') as f:
                    schema_data = yaml.safe_load(f)
                    
                if not isinstance(schema_data, dict):
                    raise ConfigurationError(
                        "Invalid schema format",
                        {"schema": schema_type}
                    )
                    
                self._schemas[schema_type] = ConfigSchema(**schema_data)
                logger.debug("Loaded schema: {}", schema_type)
                
        except Exception as e:
            raise ConfigurationError("Failed to load schemas", {"error": str(e)})

    def get_schema(self, schema_type: str) -> Optional[ConfigSchema]:
        """Get schema by type."""
        return self._schemas.get(schema_type)

    def validate_config(
            self,
            config_type: str,
            config_data: Dict[str, Any]
    ) -> List[str]:
        """Validate configuration against schema.
        
        Args:
            config_type: Type of configuration to validate
            config_data: Configuration data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        schema = self.get_schema(config_type)
        if not schema:
            raise ConfigurationError(
                "Schema not found",
                {
                    "config_type": config_type,
                    "available_schemas": list(self._schemas.keys())
                }
            )
            
        try:
            errors = []
            self._validate_against_schema(config_data, schema, "", errors)
            return errors
        except Exception as e:
            logger.error("Unexpected validation error: {}", e)
            raise ConfigurationError(
                "Validation failed",
                {
                    "config_type": config_type,
                    "error": str(e)
                }
            )
