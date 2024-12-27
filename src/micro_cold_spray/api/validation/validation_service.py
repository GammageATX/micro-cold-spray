"""Validation service implementation."""

import os
import yaml
from typing import Dict, Any, List
from datetime import datetime
from loguru import logger
from fastapi import status

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.validation.validators.hardware_validator import HardwareValidator
from micro_cold_spray.api.validation.validators.parameter_validator import ParameterValidator
from micro_cold_spray.api.validation.validators.pattern_validator import PatternValidator
from micro_cold_spray.api.validation.validators.sequence_validator import SequenceValidator


def load_config() -> Dict[str, Any]:
    """Load validation service configuration.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    config_path = os.path.join("config", "validation.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
        
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


class ValidationService:
    """Service for validating configurations."""

    def __init__(self):
        """Initialize validation service."""
        self._service_name = "validation"
        self._version = "1.0.0"  # Will be updated from config
        self._is_running = False
        self._start_time = None
        self._config = None
        
        # Initialize validators to None
        self._validation_rules = {}
        self._hardware_validator = None
        self._parameter_validator = None
        self._pattern_validator = None
        self._sequence_validator = None
        
        logger.info(f"{self._service_name} service initialized")
        
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
        """Get service uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            logger.info(f"Initializing {self.service_name} service...")
            
            # Load config
            self._config = load_config()
            self._version = self._config.get("version", self._version)
            
            # Load validation rules
            self._validation_rules = self._config.get("validation", {})
            if not self._validation_rules:
                raise ValueError("No validation rules defined in config")
                
            # Initialize validators
            self._hardware_validator = HardwareValidator(self._validation_rules)
            self._parameter_validator = ParameterValidator(self._validation_rules)
            self._pattern_validator = PatternValidator(self._validation_rules)
            self._sequence_validator = SequenceValidator(self._validation_rules)
            
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            # Initialize if not already initialized
            if not all([
                self._hardware_validator,
                self._parameter_validator,
                self._pattern_validator,
                self._sequence_validator
            ]):
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

            # 1. Clear validators
            self._hardware_validator = None
            self._parameter_validator = None
            self._pattern_validator = None
            self._sequence_validator = None
            
            # 2. Clear validation rules
            self._validation_rules.clear()
            
            # 3. Reset service state
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
            # Get health from components
            components = {
                "hardware_validator": ComponentHealth(
                    status="ok" if self._hardware_validator else "error",
                    error=None if self._hardware_validator else "Component not initialized"
                ),
                "parameter_validator": ComponentHealth(
                    status="ok" if self._parameter_validator else "error",
                    error=None if self._parameter_validator else "Component not initialized"
                ),
                "pattern_validator": ComponentHealth(
                    status="ok" if self._pattern_validator else "error",
                    error=None if self._pattern_validator else "Component not initialized"
                ),
                "sequence_validator": ComponentHealth(
                    status="ok" if self._sequence_validator else "error",
                    error=None if self._sequence_validator else "Component not initialized"
                )
            }
            
            # Overall status is error if any component is in error
            overall_status = "error" if any(c.status == "error" for c in components.values()) else "ok"
            
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
                components={name: ComponentHealth(status="error", error=error_msg)
                            for name in ["hardware_validator", "parameter_validator",
                            "pattern_validator", "sequence_validator"]}
            )

    async def validate_hardware(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate hardware configuration."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"{self.service_name} service not running"
            )
            
        return await self._hardware_validator.validate(data)

    async def validate_parameters(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameter configuration."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"{self.service_name} service not running"
            )
            
        return await self._parameter_validator.validate(data)

    async def validate_pattern(self, pattern_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern configuration."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"{self.service_name} service not running"
            )
            
        return await self._pattern_validator.validate(pattern_type, data)

    async def validate_sequence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sequence configuration."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"{self.service_name} service not running"
            )
            
        return await self._sequence_validator.validate(data)
