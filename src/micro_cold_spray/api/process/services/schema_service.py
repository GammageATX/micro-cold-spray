"""Schema service for process API."""

import yaml
from typing import Dict, Any, List
from datetime import datetime
from fastapi import status
from loguru import logger
from pathlib import Path

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth


class SchemaService:
    """Service for managing process schemas."""

    def __init__(self, version: str = "1.0.0"):
        """Initialize schema service."""
        self._service_name = "schema"
        self._version = version
        self._is_running = False
        self._start_time = None
        
        # Initialize components to None
        self._schemas: Dict[str, Dict] = {}
        self._failed_schemas = {}
        self._schema_dir = Path("schemas/process")
        
        logger.info(f"{self.service_name} service initialized")

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            # Create schema directory if it doesn't exist
            self._schema_dir.mkdir(parents=True, exist_ok=True)
            
            # Load all schema files
            await self._load_schemas()
            
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def _load_schemas(self) -> None:
        """Load schemas from files."""
        try:
            if not self._schema_dir.exists():
                return
                
            for schema_file in self._schema_dir.glob("*.yaml"):
                try:
                    with open(schema_file, "r") as f:
                        self._schemas[schema_file.stem] = yaml.safe_load(f)
                    logger.info(f"Loaded schema: {schema_file.stem}")
                    
                except Exception as e:
                    logger.error(f"Failed to load schema {schema_file}: {e}")
                    self._failed_schemas[schema_file.stem] = str(e)
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to load schemas: {e}")

    async def _attempt_recovery(self) -> None:
        """Attempt to recover failed schemas."""
        if self._failed_schemas:
            logger.info(f"Attempting to recover {len(self._failed_schemas)} failed schemas...")
            await self._load_schemas()

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            self._is_running = True
            self._start_time = datetime.now()
            logger.info(f"{self.service_name} service started")
            
        except Exception as e:
            self._is_running = False
            self._start_time = None
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
            
            # Clear schema data
            self._schemas.clear()
            
            # Reset service state
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
            # Attempt recovery of failed schemas
            await self._attempt_recovery()
            
            # Check component health
            components = {
                "schemas": ComponentHealth(
                    status="ok" if self._schemas else "error",
                    error=None if self._schemas else "No schemas loaded"
                )
            }
            
            # Add failed schemas component if any exist
            if self._failed_schemas:
                failed_list = ", ".join(self._failed_schemas.keys())
                components["failed_schemas"] = ComponentHealth(
                    status="error",
                    error=f"Failed schemas: {failed_list}"
                )
            
            # Overall status is error only if no schemas loaded
            overall_status = "error" if not self._schemas else "ok"
            if not self.is_running:
                overall_status = "error"
            
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
                components={"schemas": ComponentHealth(status="error", error=error_msg)}
            )

    async def list_schemas(self) -> List[str]:
        """List available schemas."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running"
            )
        
        return list(self._schemas.keys())

    async def get_schema(self, name: str) -> Dict[str, Any]:
        """Get schema by name."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if name not in self._schemas:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Schema '{name}' not found"
                )
                
            return self._schemas[name]
            
        except Exception as e:
            error_msg = f"Failed to get schema {name}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def validate(self, name: str, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate data against schema."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if name not in self._schemas:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Schema '{name}' not found"
                )
            
            schema = self._schemas[name]
            errors = []
            
            # Basic structure validation
            if schema["root_key"] not in data:
                errors.append(f"Missing root key '{schema['root_key']}'")
                return False, errors
                
            # Required fields
            content = data[schema["root_key"]]
            for field in schema["required_fields"]:
                if field not in content:
                    errors.append(f"Missing required field '{field}'")
                    
            # Field types
            for field, field_type in schema["field_types"].items():
                if field in content:
                    if field_type == "number":
                        if not isinstance(content[field], (int, float)):
                            errors.append(f"Field '{field}' must be a number")
                    elif field_type == "integer":
                        if not isinstance(content[field], int):
                            errors.append(f"Field '{field}' must be an integer")
                    elif field_type == "string":
                        if not isinstance(content[field], str):
                            errors.append(f"Field '{field}' must be a string")
                            
            # Field ranges
            for field, range_info in schema.get("field_ranges", {}).items():
                if field in content:
                    value = content[field]
                    if "min" in range_info and value < range_info["min"]:
                        errors.append(f"Field '{field}' must be >= {range_info['min']}")
                    if "max" in range_info and value > range_info["max"]:
                        errors.append(f"Field '{field}' must be <= {range_info['max']}")
                        
            return len(errors) == 0, errors
            
        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )
