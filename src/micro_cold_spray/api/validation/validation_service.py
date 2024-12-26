"""Validation service."""

import os
import yaml
from typing import Dict, Any, List
from loguru import logger
from fastapi import status

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.validation.validators.hardware_validator import HardwareValidator
from micro_cold_spray.api.validation.validators.parameter_validator import ParameterValidator
from micro_cold_spray.api.validation.validators.pattern_validator import PatternValidator
from micro_cold_spray.api.validation.validators.sequence_validator import SequenceValidator


class ValidationService:
    """Service for validating configurations."""

    def __init__(self):
        """Initialize validation service."""
        self.version = "1.0.0"
        self._validation_rules = self._load_validation_rules()
        self._hardware_validator = HardwareValidator(self._validation_rules)
        self._parameter_validator = ParameterValidator(self._validation_rules)
        self._pattern_validator = PatternValidator(self._validation_rules)
        self._sequence_validator = SequenceValidator(self._validation_rules)

    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules from config file.
        
        Returns:
            Validation rules dictionary
            
        Raises:
            HTTPException: If rules cannot be loaded
        """
        try:
            config_path = os.path.join("config", "validation.yaml")
            if not os.path.exists(config_path):
                logger.warning("No validation rules file found")
                return {}
                
            with open(config_path, "r") as f:
                rules = yaml.safe_load(f)
                
            if not rules:
                logger.warning("Empty validation rules file")
                return {}
                
            return rules
            
        except Exception as e:
            logger.error(f"Failed to load validation rules: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to load validation rules: {str(e)}"
            )

    async def validate_hardware(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate hardware configuration.
        
        Args:
            data: Hardware configuration to validate
            
        Returns:
            Dict containing:
                - valid: Whether validation passed
                - errors: List of error messages
                - warnings: List of warning messages
        """
        return await self._hardware_validator.validate(data)

    async def validate_parameter(self, parameter_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameter configuration.
        
        Args:
            parameter_type: Type of parameter to validate
            data: Parameter configuration to validate
            
        Returns:
            Dict containing:
                - valid: Whether validation passed
                - errors: List of error messages
                - warnings: List of warning messages
        """
        return await self._parameter_validator.validate(parameter_type, data)

    async def validate_pattern(self, pattern_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern configuration.
        
        Args:
            pattern_type: Type of pattern to validate
            data: Pattern configuration to validate
            
        Returns:
            Dict containing:
                - valid: Whether validation passed
                - errors: List of error messages
                - warnings: List of warning messages
        """
        return await self._pattern_validator.validate(pattern_type, data)

    async def validate_sequence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sequence configuration.
        
        Args:
            data: Sequence configuration to validate
            
        Returns:
            Dict containing:
                - valid: Whether validation passed
                - errors: List of error messages
                - warnings: List of warning messages
        """
        return await self._sequence_validator.validate(data)

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Dict[str, Any]: Health status
        """
        try:
            # Check if validation rules are loaded
            rules_loaded = len(self._validation_rules) > 0
            
            return {
                "status": "ok" if rules_loaded else "error",
                "service": "validation",
                "version": self.version,
                "is_running": True,
                "error": None if rules_loaded else "No validation rules loaded",
                "components": {
                    "hardware_validator": {
                        "status": "ok" if rules_loaded else "error",
                        "error": None if rules_loaded else "No validation rules"
                    },
                    "parameter_validator": {
                        "status": "ok" if rules_loaded else "error",
                        "error": None if rules_loaded else "No validation rules"
                    },
                    "pattern_validator": {
                        "status": "ok" if rules_loaded else "error",
                        "error": None if rules_loaded else "No validation rules"
                    },
                    "sequence_validator": {
                        "status": "ok" if rules_loaded else "error",
                        "error": None if rules_loaded else "No validation rules"
                    }
                }
            }
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            return {
                "status": "error",
                "service": "validation",
                "version": self.version,
                "is_running": False,
                "error": error_msg,
                "components": {
                    "hardware_validator": {"status": "error", "error": error_msg},
                    "parameter_validator": {"status": "error", "error": error_msg},
                    "pattern_validator": {"status": "error", "error": error_msg},
                    "sequence_validator": {"status": "error", "error": error_msg}
                }
            }
