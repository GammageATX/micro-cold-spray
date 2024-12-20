"""Validation service for checking data against rules."""

from typing import Dict, Any
from datetime import datetime
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config import ConfigService
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.validation.validators import (
    PatternValidator,
    SequenceValidator,
    HardwareValidator,
    ParameterValidator
)


class ValidationService(ConfigurableService):
    """Service for validating data against rules."""
    
    def __init__(
        self,
        config_service: ConfigService,
        message_broker: MessagingService
    ):
        """Initialize validation service.
        
        Args:
            config_service: Configuration service
            message_broker: Message broker service
        """
        super().__init__(service_name="validation", config_service=config_service)
        self._message_broker = message_broker
        self._validation_rules = {}
        
        # Initialize specialized validators
        self._pattern_validator = None
        self._sequence_validator = None
        self._hardware_validator = None
        self._parameter_validator = None
        
    async def initialize(self) -> None:
        """Initialize validation service.
        
        Raises:
            HTTPException: If initialization fails
        """
        try:
            await super().initialize()
            
            # Load validation rules
            config = await self._config_service.get_config("process")
            if not config or not config.data:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="No process configuration found"
                )
                
            process_config = config.data
            if "validation" not in process_config:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="No validation rules found in process configuration"
                )
                
            self._validation_rules = process_config["validation"]
            logger.info("Loaded validation rules successfully")
            
            # Initialize validators
            self._pattern_validator = PatternValidator(
                self._validation_rules,
                self._config_service,
                self._message_broker
            )
            self._sequence_validator = SequenceValidator(
                self._validation_rules,
                self._message_broker
            )
            self._hardware_validator = HardwareValidator(
                self._validation_rules,
                self._message_broker
            )
            self._parameter_validator = ParameterValidator(
                self._validation_rules,
                self._message_broker
            )
            
            # Subscribe to validation requests
            await self._message_broker.subscribe(
                "validation/request",
                self._handle_validation_request
            )
            logger.info("Validation service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to start validation service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to start validation service",
                context={"error": str(e)},
                cause=e
            )
        
    async def _handle_validation_request(self, data: Dict[str, Any]) -> None:
        """Handle validation request.
        
        Args:
            data: Request data containing:
                - type: Type of validation to perform
                - data: Data to validate
                - request_id: Optional request ID
        """
        try:
            validation_type = data["type"]
            validation_data = data["data"]
            
            # Validate based on type
            if validation_type == "parameters":
                result = await self._parameter_validator.validate(validation_data)
            elif validation_type == "pattern":
                result = await self._pattern_validator.validate(validation_data)
            elif validation_type == "sequence":
                result = await self._sequence_validator.validate(validation_data)
            elif validation_type == "hardware":
                result = await self._hardware_validator.validate(validation_data)
            else:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Unknown validation type",
                    context={"type": validation_type}
                )
                
            # Send validation response
            await self._message_broker.publish(
                "validation/response",
                {
                    "request_id": data.get("request_id"),
                    "type": validation_type,
                    "valid": result["valid"],
                    "errors": result.get("errors", []),
                    "warnings": result.get("warnings", []),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            await self._message_broker.publish(
                "validation/response",
                {
                    "request_id": data.get("request_id"),
                    "type": data.get("type"),
                    "valid": False,
                    "errors": [str(e)],
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def validate_parameters(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate process parameters.
        
        Args:
            data: Parameter data to validate
            
        Returns:
            Dict containing validation results
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            return await self._parameter_validator.validate(data)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Parameter validation failed",
                context={"error": str(e)},
                cause=e
            )

    async def validate_pattern(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern definition.
        
        Args:
            data: Pattern data to validate
            
        Returns:
            Dict containing validation results
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            return await self._pattern_validator.validate(data)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Pattern validation failed",
                context={"error": str(e)},
                cause=e
            )

    async def validate_sequence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sequence definition.
        
        Args:
            data: Sequence data to validate
            
        Returns:
            Dict containing validation results
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            return await self._sequence_validator.validate(data)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Sequence validation failed",
                context={"error": str(e)},
                cause=e
            )

    async def validate_hardware(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate hardware conditions.
        
        Args:
            data: Hardware data to validate
            
        Returns:
            Dict containing validation results
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            return await self._hardware_validator.validate(data)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Hardware validation failed",
                context={"error": str(e)},
                cause=e
            )

    async def get_rules(self, rule_type: str) -> Dict[str, Any]:
        """Get validation rules for specified type.
        
        Args:
            rule_type: Type of rules to retrieve
            
        Returns:
            Dict containing rules
            
        Raises:
            HTTPException: If rules not found
        """
        if rule_type not in self._validation_rules:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Unknown rule type",
                context={"type": rule_type, "valid_types": list(self._validation_rules.keys())}
            )
        return self._validation_rules[rule_type]
