"""Validation service for checking data against rules."""

import os
import yaml
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.validation.validators import (
    PatternValidator,
    SequenceValidator,
    HardwareValidator,
    ParameterValidator
)


class ValidationService:
    """Service for validating system data and configurations."""

    def __init__(self):
        """Initialize validation service."""
        self._service_name = "validation"
        self._is_running = False
        self._validation_rules = {}
        self._message_broker: Optional[MessagingService] = None
        self._pattern_validator: Optional[PatternValidator] = None
        self._sequence_validator: Optional[SequenceValidator] = None
        self._hardware_validator: Optional[HardwareValidator] = None
        self._parameter_validator: Optional[ParameterValidator] = None
        logger.info("Validation service initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def initialize(
        self,
        message_broker: MessagingService
    ) -> None:
        """Initialize validation service.
        
        Args:
            message_broker: Message broker for hardware checks
            
        Raises:
            HTTPException: If initialization fails
        """
        try:
            self._message_broker = message_broker

            # Load validation rules
            config_dir = os.path.join(os.getcwd(), "config")
            validation_file = os.path.join(config_dir, "validation.yaml")
            
            if not os.path.exists(validation_file):
                raise FileNotFoundError(f"Validation config not found: {validation_file}")
                
            with open(validation_file, "r") as f:
                self._validation_rules = yaml.safe_load(f)

            # Initialize validators
            self._pattern_validator = PatternValidator(
                self._validation_rules,
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
                "validation_request",
                self._handle_validation_request
            )

            self._is_running = True
            logger.info("Validation service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize validation service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to initialize validation service: {str(e)}"
            )

    async def stop(self) -> None:
        """Stop validation service."""
        try:
            if self._message_broker:
                await self._message_broker.unsubscribe(
                    "validation/request",
                    self._handle_validation_request
                )
            self._is_running = False
            logger.info("Validation service stopped")
        except Exception as e:
            logger.error(f"Failed to stop validation service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to stop validation service: {str(e)}"
            )

    async def validate_pattern(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern data.
        
        Args:
            pattern_data: Pattern data to validate
            
        Returns:
            Validation results
        """
        if not self._pattern_validator:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Pattern validator not initialized"
            )
        return await self._pattern_validator.validate(pattern_data)

    async def validate_sequence(self, sequence_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sequence data.
        
        Args:
            sequence_data: Sequence data to validate
            
        Returns:
            Validation results
        """
        if not self._sequence_validator:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Sequence validator not initialized"
            )
        return await self._sequence_validator.validate(sequence_data)

    async def validate_hardware(self, hardware_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate hardware data.
        
        Args:
            hardware_data: Hardware data to validate
            
        Returns:
            Validation results
        """
        if not self._hardware_validator:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Hardware validator not initialized"
            )
        return await self._hardware_validator.validate(hardware_data)

    async def validate_parameters(self, parameter_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameter data.
        
        Args:
            parameter_data: Parameter data to validate
            
        Returns:
            Validation results
        """
        if not self._parameter_validator:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Parameter validator not initialized"
            )
        return await self._parameter_validator.validate(parameter_data)

    async def _handle_validation_request(self, data: Dict[str, Any]) -> None:
        """Handle validation request message.
        
        Args:
            data: Request data containing:
                - type: Type of validation
                - data: Data to validate
                - request_id: Optional request ID
        """
        try:
            validation_type = data.get("type")
            if not validation_type:
                raise ValueError("Missing validation type")

            validation_data = data.get("data", {})
            result = None

            # Route to appropriate validator
            if validation_type == "pattern":
                result = await self.validate_pattern(validation_data)
            elif validation_type == "sequence":
                result = await self.validate_sequence(validation_data)
            elif validation_type == "hardware":
                result = await self.validate_hardware(validation_data)
            elif validation_type == "parameters":
                result = await self.validate_parameters(validation_data)
            else:
                raise ValueError(f"Unknown validation type: {validation_type}")

            # Add metadata and publish response
            result["request_id"] = data.get("request_id")
            result["type"] = validation_type
            result["timestamp"] = datetime.now().isoformat()

            await self._message_broker.publish("validation/response", result)

        except Exception as e:
            logger.error(f"Validation request failed: {e}")
            error_response = {
                "request_id": data.get("request_id"),
                "type": data.get("type"),
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }
            await self._message_broker.publish("validation/response", error_response)
