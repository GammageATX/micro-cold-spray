"""Validation service for checking data against rules."""

from typing import Dict, Any
from datetime import datetime

from ..base import BaseService
from ..config import ConfigService
from ..messaging import MessagingService
from .exceptions import ValidationError
from .validators import (
    PatternValidator,
    SequenceValidator,
    HardwareValidator,
    ParameterValidator
)


class ValidationService(BaseService):
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
        
    async def _start(self) -> None:
        """Initialize validation service."""
        try:
            # Load validation rules
            config = await self._config_service.get_config("process")
            self._validation_rules = config["process"]["validation"]
            
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
            
        except Exception as e:
            raise ValidationError("Failed to start validation service", {"error": str(e)})
        
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
                raise ValidationError(f"Unknown validation type: {validation_type}")
                
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
            ValidationError: If validation fails
        """
        return await self._parameter_validator.validate(data)

    async def validate_pattern(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern definition.
        
        Args:
            data: Pattern data to validate
            
        Returns:
            Dict containing validation results
            
        Raises:
            ValidationError: If validation fails
        """
        return await self._pattern_validator.validate(data)

    async def validate_sequence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sequence definition.
        
        Args:
            data: Sequence data to validate
            
        Returns:
            Dict containing validation results
            
        Raises:
            ValidationError: If validation fails
        """
        return await self._sequence_validator.validate(data)

    async def validate_hardware(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate hardware conditions.
        
        Args:
            data: Hardware data to validate
            
        Returns:
            Dict containing validation results
            
        Raises:
            ValidationError: If validation fails
        """
        return await self._hardware_validator.validate(data)

    async def get_rules(self, rule_type: str) -> Dict[str, Any]:
        """Get validation rules for specified type.
        
        Args:
            rule_type: Type of rules to retrieve
            
        Returns:
            Dict containing rules
            
        Raises:
            ValidationError: If rules not found
        """
        if rule_type not in self._validation_rules:
            raise ValidationError(f"Unknown rule type: {rule_type}")
        return self._validation_rules[rule_type]
