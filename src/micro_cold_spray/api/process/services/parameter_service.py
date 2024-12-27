"""Parameter service implementation."""

import os
import time
import yaml
from typing import Dict, Any, List, Optional
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.process.models.process_models import ParameterSet


class ParameterService:
    """Service for managing process parameters."""

    def __init__(self):
        """Initialize parameter service."""
        self._start_time = time.time()
        self._is_running = False
        self._version = "1.0.0"
        self._service_name = "parameter"
        self._parameter_sets: Dict[str, ParameterSet] = {}

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
        return time.time() - self._start_time

    async def initialize(self) -> None:
        """Initialize service.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            logger.info("Initializing parameter service...")
            
            # Load config
            config_path = os.path.join("config", "process.yaml")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                    if "parameter" in config:
                        self._version = config["parameter"].get("version", self._version)
                        
                        # Load parameter sets from config
                        parameter_sets = config["parameter"].get("parameter_sets", {})
                        for param_id, param_data in parameter_sets.items():
                            self._parameter_sets[param_id] = ParameterSet(
                                id=param_id,
                                name=param_data.get("name", ""),
                                description=param_data.get("description", ""),
                                parameters=param_data.get("parameters", {})
                            )
            
            logger.info("Parameter service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize parameter service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def start(self) -> None:
        """Start service.
        
        Raises:
            Exception: If start fails
        """
        try:
            logger.info("Starting parameter service...")
            self._is_running = True
            logger.info("Parameter service started")
            
        except Exception as e:
            error_msg = f"Failed to start parameter service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def stop(self) -> None:
        """Stop service.
        
        Raises:
            Exception: If stop fails
        """
        try:
            logger.info("Stopping parameter service...")
            self._is_running = False
            logger.info("Parameter service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop parameter service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def health(self) -> ServiceHealth:
        """Get service health status.
        
        Returns:
            ServiceHealth: Service health status
        """
        try:
            status = "healthy"
            error = None
            
            if not self.is_running:
                status = "error"
                error = "Service not running"
                
            return ServiceHealth(
                status=status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=error,
                components={}
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

    async def list_parameter_sets(self) -> List[ParameterSet]:
        """List available parameter sets.
        
        Returns:
            List[ParameterSet]: List of parameter sets
            
        Raises:
            Exception: If listing fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            return list(self._parameter_sets.values())
            
        except Exception as e:
            error_msg = "Failed to list parameter sets"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)

    async def get_parameter_set(self, param_id: str) -> ParameterSet:
        """Get parameter set by ID.
        
        Args:
            param_id: Parameter set identifier
            
        Returns:
            ParameterSet: Parameter set
            
        Raises:
            Exception: If parameter set not found or retrieval fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if param_id not in self._parameter_sets:
                raise Exception(f"Parameter set {param_id} not found")
                
            return self._parameter_sets[param_id]
            
        except Exception as e:
            error_msg = f"Failed to get parameter set {param_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)

    async def create_parameter_set(self, parameter_set: ParameterSet) -> ParameterSet:
        """Create new parameter set.
        
        Args:
            parameter_set: Parameter set to create
            
        Returns:
            ParameterSet: Created parameter set
            
        Raises:
            Exception: If creation fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if parameter_set.id in self._parameter_sets:
                raise Exception(f"Parameter set {parameter_set.id} already exists")
                
            self._parameter_sets[parameter_set.id] = parameter_set
            logger.info(f"Created parameter set {parameter_set.id}")
            
            return parameter_set
            
        except Exception as e:
            error_msg = f"Failed to create parameter set {parameter_set.id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)

    async def update_parameter_set(self, parameter_set: ParameterSet) -> ParameterSet:
        """Update existing parameter set.
        
        Args:
            parameter_set: Parameter set to update
            
        Returns:
            ParameterSet: Updated parameter set
            
        Raises:
            Exception: If update fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if parameter_set.id not in self._parameter_sets:
                raise Exception(f"Parameter set {parameter_set.id} not found")
                
            self._parameter_sets[parameter_set.id] = parameter_set
            logger.info(f"Updated parameter set {parameter_set.id}")
            
            return parameter_set
            
        except Exception as e:
            error_msg = f"Failed to update parameter set {parameter_set.id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)

    async def delete_parameter_set(self, param_id: str) -> None:
        """Delete parameter set.
        
        Args:
            param_id: Parameter set identifier
            
        Raises:
            Exception: If deletion fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if param_id not in self._parameter_sets:
                raise Exception(f"Parameter set {param_id} not found")
                
            del self._parameter_sets[param_id]
            logger.info(f"Deleted parameter set {param_id}")
            
        except Exception as e:
            error_msg = f"Failed to delete parameter set {param_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)
