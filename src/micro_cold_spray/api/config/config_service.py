"""Configuration service."""

import os
import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from loguru import logger

from fastapi import status, HTTPException
from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.config.services.file_service import FileService
from micro_cold_spray.api.config.services.format_service import FormatService
from micro_cold_spray.api.config.services.schema_service import SchemaService
import jsonschema


# Default paths
DEFAULT_CONFIG_PATH = os.path.join(os.getcwd(), "config")
DEFAULT_SCHEMA_PATH = os.path.join(DEFAULT_CONFIG_PATH, "schemas")


class ConfigService:
    """Configuration service."""

    def __init__(self, version: str = "1.0.0"):
        """Initialize service."""
        self._service_name = "config"
        self._version = version
        self._is_running = False
        self._start_time = None
        
        # Initialize components to None
        self._config = None
        self._file = None
        self._format = None
        self._schema = None
        
        # Track failed configurations
        self._failed_configs = {}
        
        logger.info(f"{self.service_name} service initialized")

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    @property
    def uptime(self) -> float:
        """Get service uptime."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            logger.info(f"Initializing {self.service_name} service...")
            
            # Load config
            await self._load_config()
            
            # Initialize services with config
            try:
                self._file = FileService(
                    base_path=self._config["components"]["file"]["base_path"],
                    version=self._config["components"]["file"]["version"]
                )
                self._failed_configs.pop("file", None)
            except Exception as e:
                self._failed_configs["file"] = str(e)
                logger.error(f"Failed to initialize file service: {e}")
            
            try:
                self._format = FormatService(
                    enabled_formats=self._config["components"]["format"]["enabled_formats"],
                    version=self._config["components"]["format"]["version"]
                )
                self._failed_configs.pop("format", None)
            except Exception as e:
                self._failed_configs["format"] = str(e)
                logger.error(f"Failed to initialize format service: {e}")
            
            try:
                self._schema = SchemaService(
                    schema_path=self._config["components"]["schema"]["schema_path"],
                    version=self._config["components"]["schema"]["version"]
                )
                self._failed_configs.pop("schema", None)
            except Exception as e:
                self._failed_configs["schema"] = str(e)
                logger.error(f"Failed to initialize schema service: {e}")
            
            # Initialize services in order
            if self._file:
                await self._file.initialize()
            if self._format:
                await self._format.initialize()
            if self._schema:
                await self._schema.initialize()
            
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def _load_config(self) -> None:
        """Load configuration."""
        try:
            with open("config/config.yaml", "r") as f:
                self._config = yaml.safe_load(f)
            self._version = self._config["version"]
            logger.info(f"Loaded config version {self._version}")
            self._failed_configs.pop("main", None)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._failed_configs["main"] = str(e)
            self._config = {
                "version": self._version,
                "components": {
                    "file": {
                        "version": "1.0.0",
                        "base_path": DEFAULT_CONFIG_PATH
                    },
                    "format": {
                        "version": "1.0.0",
                        "enabled_formats": ["yaml", "json"]
                    },
                    "schema": {
                        "version": "1.0.0",
                        "schema_path": DEFAULT_SCHEMA_PATH
                    }
                }
            }

    async def _attempt_recovery(self) -> None:
        """Attempt to recover failed configurations."""
        if self._failed_configs:
            logger.info(f"Attempting to recover {len(self._failed_configs)} failed configs...")
            
            # Try to reload main config
            if "main" in self._failed_configs:
                await self._load_config()
            
            # Try to reinitialize failed services
            if "file" in self._failed_configs and not self._file:
                try:
                    self._file = FileService(
                        base_path=self._config["components"]["file"]["base_path"],
                        version=self._config["components"]["file"]["version"]
                    )
                    await self._file.initialize()
                    self._failed_configs.pop("file", None)
                except Exception as e:
                    logger.error(f"Failed to recover file service: {e}")
            
            if "format" in self._failed_configs and not self._format:
                try:
                    self._format = FormatService(
                        enabled_formats=self._config["components"]["format"]["enabled_formats"],
                        version=self._config["components"]["format"]["version"]
                    )
                    await self._format.initialize()
                    self._failed_configs.pop("format", None)
                except Exception as e:
                    logger.error(f"Failed to recover format service: {e}")
            
            if "schema" in self._failed_configs and not self._schema:
                try:
                    self._schema = SchemaService(
                        schema_path=self._config["components"]["schema"]["schema_path"],
                        version=self._config["components"]["schema"]["version"]
                    )
                    await self._schema.initialize()
                    self._failed_configs.pop("schema", None)
                except Exception as e:
                    logger.error(f"Failed to recover schema service: {e}")

    async def start(self) -> None:
        """Start service."""
        try:
            logger.info(f"Starting {self.service_name} service...")
            
            # Initialize first
            await self.initialize()
            
            # Start services in order
            if self._file:
                await self._file.start()
            if self._format:
                await self._format.start()
            if self._schema:
                await self._schema.start()
            
            self._is_running = True
            self._start_time = datetime.now()
            logger.info(f"{self.service_name} service started successfully")
            
        except Exception as e:
            self._is_running = False
            error_msg = f"Failed to start {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service not running"
                )

            # Stop services in reverse order
            if self._schema:
                await self._schema.stop()
            if self._format:
                await self._format.stop()
            if self._file:
                await self._file.stop()

            self._is_running = False
            self._start_time = None
            logger.info(f"{self.service_name} service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def health(self) -> ServiceHealth:
        """Get service health status."""
        try:
            # Attempt recovery of failed configs
            await self._attempt_recovery()
            
            # Get health from all services
            file_health = await self._file.health() if self._file else None
            format_health = await self._format.health() if self._format else None
            schema_health = await self._schema.health() if self._schema else None
            
            # Build component statuses
            components = {
                "file": ComponentHealth(
                    status=file_health.status if file_health else "error",
                    error=file_health.error if file_health else "Component not initialized"
                ),
                "format": ComponentHealth(
                    status=format_health.status if format_health else "error",
                    error=format_health.error if format_health else "Component not initialized"
                ),
                "schema": ComponentHealth(
                    status=schema_health.status if schema_health else "error",
                    error=schema_health.error if schema_health else "Component not initialized"
                )
            }
            
            # Add failed configs component if any exist
            if self._failed_configs:
                failed_list = ", ".join(self._failed_configs.keys())
                components["failed_configs"] = ComponentHealth(
                    status="error",
                    error=f"Failed configurations: {failed_list}"
                )
            
            # Overall status is error only if all components failed
            overall_status = "error" if not any([self._file, self._format, self._schema]) else "ok"
            
            return ServiceHealth(
                status=overall_status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if overall_status == "ok" else "One or more components in error state",
                components=components
            )
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service=self.service_name,
                version=self.version,
                is_running=False,
                uptime=self.uptime,
                error=error_msg,
                components={}
            )

    async def list_configs(self) -> list:
        """List available configurations."""
        if not self._file or not self._format:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="File or format service not initialized"
            )
        
        try:
            # Get list of files in base directory
            files = os.listdir(self._file._base_path)
            configs = []
            
            # Filter for supported formats
            for file in files:
                name, ext = os.path.splitext(file)
                if ext[1:] in self._format._enabled_formats:
                    configs.append(name)
            
            return configs
            
        except Exception as e:
            error_msg = f"Failed to list configurations: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def get_config(self, name: str) -> Dict[str, Any]:
        """Get configuration by name."""
        if not self._file or not self._format:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="File or format service not initialized"
            )
        
        try:
            # Find file with supported format
            for fmt in self._format._enabled_formats:
                file_path = os.path.join(self._file._base_path, f"{name}.{fmt}")
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        if fmt == 'json':
                            return json.loads(f.read())
                        elif fmt == 'yaml':
                            return yaml.safe_load(f)
            
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Configuration {name} not found"
            )
            
        except Exception as e:
            error_msg = f"Failed to get configuration {name}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def list_schemas(self) -> list:
        """List available schemas."""
        if not self._schema:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Schema service not initialized"
            )
        
        try:
            # Get list of files in schema directory
            files = os.listdir(self._schema._schema_path)
            schemas = []
            
            # Filter for supported formats
            for file in files:
                name, ext = os.path.splitext(file)
                if ext[1:] in ['json', 'yaml']:
                    schemas.append(name)
            
            return schemas
            
        except Exception as e:
            error_msg = f"Failed to list schemas: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def get_schema(self, name: str) -> Dict[str, Any]:
        """Get schema by name."""
        if not self._schema:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Schema service not initialized"
            )
        
        try:
            # Find schema file with supported format
            for fmt in ['json', 'yaml']:
                file_path = os.path.join(self._schema._schema_path, f"{name}.{fmt}")
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        if fmt == 'json':
                            return json.loads(f.read())
                        elif fmt == 'yaml':
                            return yaml.safe_load(f)
            
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Schema {name} not found"
            )
            
        except Exception as e:
            error_msg = f"Failed to get schema {name}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def validate_config(self, name: str, data: Dict[str, Any]) -> None:
        """Validate configuration against schema."""
        if not self._schema:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Schema service not initialized"
            )
            
        try:
            # Get schema for config
            schema = self._schema.get_schema(name)
            if not schema:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Schema not found for {name}"
                )
                
            # Validate data against schema
            try:
                validator = jsonschema.validators.Draft7Validator(schema)
                validator.validate(data)
            except jsonschema.exceptions.ValidationError as e:
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message=f"Validation failed: {str(e)}"
                )
                
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            error_msg = f"Failed to validate config {name}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def update_config(self, name: str, data: Dict[str, Any], format: str = "yaml") -> None:
        """Update configuration by name."""
        if not self._file or not self._format:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="File or format service not initialized"
            )
        
        if format not in self._format._enabled_formats:
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Unsupported format: {format}"
            )
        
        try:
            # Write config to file
            file_path = os.path.join(self._file._base_path, f"{name}.{format}")
            with open(file_path, 'w') as f:
                if format == 'json':
                    json.dump(data, f, indent=2)
                elif format == 'yaml':
                    yaml.safe_dump(data, f, default_flow_style=False)
            
        except Exception as e:
            error_msg = f"Failed to update config {name}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def update_schema(self, name: str, schema_definition: Dict[str, Any]) -> None:
        """Update schema by name.
        
        Args:
            name: Name of schema to update
            schema_definition: Schema definition to save
        """
        if not self._schema:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Schema service not initialized"
            )
            
        try:
            # Validate schema definition is valid JSON Schema
            try:
                jsonschema.Draft7Validator.check_schema(schema_definition)
            except jsonschema.exceptions.SchemaError as e:
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message=f"Invalid schema definition: {str(e)}"
                )
            
            # Write schema to file
            file_path = os.path.join(self._schema._schema_path, f"{name}.json")
            try:
                with open(file_path, 'w') as f:
                    json.dump(schema_definition, f, indent=2)
            except Exception as e:
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Failed to write schema: {str(e)}"
                )
                
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            error_msg = f"Failed to update schema {name}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )
