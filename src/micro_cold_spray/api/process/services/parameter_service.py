"""Parameter service implementation."""

import os
import time
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.process.models.process_models import ParameterSet


class ParameterService:
    """Service for managing process parameters."""

    def __init__(self, version: str = "1.0.0"):
        """Initialize parameter service."""
        self._service_name = "parameter"
        self._version = version
        self._is_running = False
        self._start_time = None
        
        # Initialize components to None
        self._parameter_sets = None
        self._failed_parameters = {}  # Track failed parameter sets
        
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
            
            # Initialize parameter sets
            self._parameter_sets = {}
            
            # Load config and parameter sets
            await self._load_parameters()
            
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def _load_parameters(self) -> None:
        """Load parameter sets from config."""
        config_path = os.path.join("config", "process.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                if "parameter" in config:
                    self._version = config["parameter"].get("version", self._version)
                    
                    # Load parameter sets from config
                    parameter_sets = config["parameter"].get("parameter_sets", {})
                    for param_id, param_data in parameter_sets.items():
                        try:
                            # Ensure required fields exist
                            if not param_data.get("name"):
                                param_data["name"] = param_id
                            if not param_data.get("description"):
                                param_data["description"] = ""
                            if not param_data.get("parameters"):
                                param_data["parameters"] = {}
                                
                            self._parameter_sets[param_id] = ParameterSet(
                                id=param_id,
                                name=param_data.get("name", ""),
                                description=param_data.get("description", ""),
                                parameters=param_data.get("parameters", {})
                            )
                            # If parameter set was previously failed, remove from failed list
                            self._failed_parameters.pop(param_id, None)
                        except Exception as e:
                            logger.error(f"Failed to load parameter set {param_id}: {e}")
                            self._failed_parameters[param_id] = str(e)

    async def _attempt_recovery(self) -> None:
        """Attempt to recover failed parameter sets."""
        if self._failed_parameters:
            logger.info(f"Attempting to recover {len(self._failed_parameters)} failed parameter sets...")
            await self._load_parameters()

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            if self._parameter_sets is None:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"{self.service_name} service not initialized"
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
            
            # 1. Clear parameter data
            self._parameter_sets.clear()
            
            # 2. Reset service state
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
            # Attempt recovery of failed parameter sets
            await self._attempt_recovery()
            
            # Check component health
            components = {
                "parameter_sets": ComponentHealth(
                    status="ok" if self._parameter_sets is not None and len(self._parameter_sets) > 0 else "error",
                    error=None if self._parameter_sets is not None and len(self._parameter_sets) > 0 else "No parameter sets loaded"
                )
            }
            
            # Add failed parameter sets component if any exist
            if self._failed_parameters:
                failed_list = ", ".join(self._failed_parameters.keys())
                components["failed_parameters"] = ComponentHealth(
                    status="error",
                    error=f"Failed parameter sets: {failed_list}"
                )
            
            # Overall status is error only if no parameter sets loaded
            overall_status = "error" if not self._parameter_sets or len(self._parameter_sets) == 0 else "ok"
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
                components={"parameter_sets": ComponentHealth(status="error", error=error_msg)}
            )

    async def list_parameter_sets(self) -> List[ParameterSet]:
        """List available parameter sets."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            return list(self._parameter_sets.values())
            
        except Exception as e:
            error_msg = "Failed to list parameter sets"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def get_parameter_set(self, param_id: str) -> ParameterSet:
        """Get parameter set by ID."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if param_id not in self._parameter_sets:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Parameter set {param_id} not found"
                )
                
            return self._parameter_sets[param_id]
            
        except Exception as e:
            error_msg = f"Failed to get parameter set {param_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def create_parameter_set(self, parameter_set: ParameterSet) -> ParameterSet:
        """Create new parameter set."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if parameter_set.id in self._parameter_sets:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Parameter set {parameter_set.id} already exists"
                )
                
            self._parameter_sets[parameter_set.id] = parameter_set
            logger.info(f"Created parameter set {parameter_set.id}")
            
            return parameter_set
            
        except Exception as e:
            error_msg = f"Failed to create parameter set {parameter_set.id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def update_parameter_set(self, parameter_set: ParameterSet) -> ParameterSet:
        """Update existing parameter set."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if parameter_set.id not in self._parameter_sets:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Parameter set {parameter_set.id} not found"
                )
                
            self._parameter_sets[parameter_set.id] = parameter_set
            logger.info(f"Updated parameter set {parameter_set.id}")
            
            return parameter_set
            
        except Exception as e:
            error_msg = f"Failed to update parameter set {parameter_set.id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )
