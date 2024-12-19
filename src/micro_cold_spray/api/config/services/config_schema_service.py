"""Configuration schema service implementation."""

import json
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import ConfigError
from micro_cold_spray.api.config.models.config_models import ConfigSchema


class ConfigSchemaService(BaseService):
    """Configuration schema service implementation."""

    def __init__(self, service_name: str, schema_dir: Path) -> None:
        """Initialize service.

        Args:
            service_name: Service name
            schema_dir: Schema directory
        """
        super().__init__(service_name)
        self._schema_dir = schema_dir
        self._schemas: Dict[str, ConfigSchema] = {}

    async def _start(self) -> None:
        """Start schema service."""
        try:
            self._schema_dir.mkdir(exist_ok=True)
            await self._load_schemas()
            logger.info("Schema service started with {} schemas", len(self._schemas))
        except Exception as e:
            raise ConfigError("Failed to start schema service", {"error": str(e)})

    async def _load_schemas(self) -> None:
        """Load all schema files."""
        try:
            for schema_file in self._schema_dir.glob("*.json"):
                schema_type = schema_file.stem
                with open(schema_file, 'r') as f:
                    schema_data = json.load(f)

                if not isinstance(schema_data, dict):
                    raise ConfigError(
                        "Invalid schema format",
                        {"schema": schema_type}
                    )

                self._schemas[schema_type] = ConfigSchema(**schema_data)
                logger.debug("Loaded schema: {}", schema_type)

        except Exception as e:
            raise ConfigError("Failed to load schemas", {"error": str(e)})

    def get_schema(self, schema_type: str) -> Optional[ConfigSchema]:
        """Get schema by type.

        Args:
            schema_type: Schema type

        Returns:
            Schema if found, None otherwise
        """
        return self._schemas.get(schema_type)

    async def add_schema(self, schema_type: str, schema: ConfigSchema) -> None:
        """Add schema.

        Args:
            schema_type: Schema type
            schema: Schema to add

        Raises:
            ConfigError: If schema already exists or save fails
        """
        if schema_type in self._schemas:
            raise ConfigError(f"Schema {schema_type} already exists")

        try:
            schema_file = self._schema_dir / f"{schema_type}.json"
            with open(schema_file, 'w') as f:
                json.dump(schema.model_dump(), f, indent=2)

            self._schemas[schema_type] = schema
            logger.info("Added schema: {}", schema_type)
        except Exception as e:
            raise ConfigError("Failed to add schema", {"error": str(e)})

    async def update_schema(self, schema_type: str, schema: ConfigSchema) -> None:
        """Update schema.

        Args:
            schema_type: Schema type
            schema: Updated schema

        Raises:
            ConfigError: If schema not found or save fails
        """
        if schema_type not in self._schemas:
            raise ConfigError(f"Schema {schema_type} not found")

        try:
            schema_file = self._schema_dir / f"{schema_type}.json"
            with open(schema_file, 'w') as f:
                json.dump(schema.model_dump(), f, indent=2)

            self._schemas[schema_type] = schema
            logger.info("Updated schema: {}", schema_type)
        except Exception as e:
            raise ConfigError("Failed to update schema", {"error": str(e)})

    async def delete_schema(self, schema_type: str) -> None:
        """Delete schema.

        Args:
            schema_type: Schema type to delete

        Raises:
            ConfigError: If schema not found or delete fails
        """
        if schema_type not in self._schemas:
            raise ConfigError(f"Schema {schema_type} not found")

        try:
            schema_file = self._schema_dir / f"{schema_type}.json"
            schema_file.unlink()
            del self._schemas[schema_type]
            logger.info("Deleted schema: {}", schema_type)
        except Exception as e:
            raise ConfigError("Failed to delete schema", {"error": str(e)})

    async def check_health(self) -> dict:
        """Check service health.

        Returns:
            Health check result
        """
        health = await super().check_health()
        health["service_info"].update({
            "schema_dir": str(self._schema_dir),
            "schema_count": len(self._schemas),
            "schemas": list(self._schemas.keys())
        })
        return health
