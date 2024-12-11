"""Sequence validator."""

from typing import Dict, Any, List
from datetime import datetime

from ...messaging import MessagingService
from ..exceptions import ValidationError
from .base import BaseValidator
from .hardware_validator import HardwareValidator


class SequenceValidator(BaseValidator):
    """Validator for spray sequences."""

    def __init__(
        self,
        validation_rules: Dict[str, Any],
        message_broker: MessagingService
    ):
        """Initialize sequence validator.
        
        Args:
            validation_rules: Validation rules from config
            message_broker: Message broker for hardware checks
        """
        super().__init__(validation_rules, message_broker)
        self._hardware_validator = HardwareValidator(validation_rules, message_broker)

    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sequence definition.
        
        Args:
            data: Sequence data to validate
            
        Returns:
            Dict containing validation results
            
        Raises:
            ValidationError: If validation fails
        """
        errors = []
        warnings = []
        
        try:
            # Check required fields
            required = self._rules["sequences"]["required_fields"]
            errors.extend(self._check_required_fields(
                data,
                required["fields"],
                "Sequence: "
            ))

            # Validate metadata
            if "metadata" in data:
                metadata_errors = await self._validate_metadata(data["metadata"])
                errors.extend(metadata_errors)

            # Validate steps
            if "steps" in data:
                # Check max steps
                max_steps = self._rules["sequences"].get("max_steps", 100)
                if len(data["steps"]) > max_steps:
                    errors.append(f"Sequence exceeds maximum steps: {max_steps}")
                
                # Validate each step
                for i, step in enumerate(data["steps"]):
                    step_errors = await self._validate_sequence_step(step)
                    errors.extend([f"Step {i+1}: {err}" for err in step_errors])

            # Validate sequence type rules
            if "type" in data:
                type_errors = await self._validate_sequence_type(data)
                errors.extend(type_errors)

            # Validate safety conditions
            if "safety" in self._rules["sequences"]:
                safety_errors = await self._validate_safety_conditions()
                errors.extend(safety_errors)

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            raise ValidationError("Sequence validation failed", {"error": str(e)})

    async def _validate_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Validate sequence metadata.
        
        Args:
            metadata: Metadata to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            # Check required fields
            required = ["name", "version", "created"]
            errors.extend(self._check_required_fields(
                metadata,
                required,
                "Metadata: "
            ))
            
            # Validate created timestamp
            if "created" in metadata:
                try:
                    datetime.fromisoformat(metadata["created"])
                except ValueError:
                    errors.append("Metadata: Invalid created timestamp format")
                    
        except Exception as e:
            errors.append(f"Metadata validation error: {str(e)}")
        return errors

    async def _validate_sequence_step(self, step: Dict[str, Any]) -> List[str]:
        """Validate sequence step.
        
        Args:
            step: Step data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["sequences"]["step_fields"]
            
            # Check required fields
            errors.extend(self._check_required_fields(
                step,
                rules["required_fields"]["fields"]
            ))
            
            # Check for unknown fields
            if "optional_fields" in rules:
                valid_fields = (
                    rules["required_fields"]["fields"] +
                    rules["optional_fields"]["fields"]
                )
                errors.extend(self._check_unknown_fields(
                    step,
                    valid_fields
                ))
            
            # Validate step type-specific fields
            if "action" in step:
                action_errors = await self._validate_action_step(step)
                errors.extend(action_errors)
            elif "pattern" in step:
                pattern_errors = await self._validate_pattern_step(step)
                errors.extend(pattern_errors)
                
        except Exception as e:
            errors.append(f"Step validation error: {str(e)}")
        return errors

    async def _validate_sequence_type(self, data: Dict[str, Any]) -> List[str]:
        """Validate sequence type rules.
        
        Args:
            data: Sequence data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            sequence_type = data["type"]
            type_rules = self._rules["sequences"]["types"].get(sequence_type)
            
            if not type_rules:
                errors.append(f"Unknown sequence type: {sequence_type}")
                return errors
            
            # Check required steps
            if "required_steps" in type_rules:
                required_steps = type_rules["required_steps"]
                found_steps = set()
                
                for step in data["steps"]:
                    if "action" in step:
                        found_steps.add(step["action"])
                
                for required in required_steps:
                    if required not in found_steps:
                        errors.append(f"Missing required step: {required}")
            
            # Check step order
            if type_rules.get("check_order", False) and "step_order" in type_rules:
                order_errors = self._validate_step_order(
                    data["steps"],
                    type_rules["step_order"]
                )
                errors.extend(order_errors)
                
        except Exception as e:
            errors.append(f"Sequence type validation error: {str(e)}")
        return errors

    async def _validate_safety_conditions(self) -> List[str]:
        """Validate safety conditions.
        
        Returns:
            List of error messages
        """
        try:
            # Use hardware validator for safety checks
            result = await self._hardware_validator.validate({})
            return result.get("errors", [])
            
        except Exception as e:
            return [f"Safety validation error: {str(e)}"]

    async def _validate_action_step(self, step: Dict[str, Any]) -> List[str]:
        """Validate action step.
        
        Args:
            step: Step data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            action = step["action"]
            parameters = step.get("parameters", {})
            
            # Check action type is valid
            valid_actions = self._rules["sequences"].get("valid_actions", [])
            if action not in valid_actions:
                errors.append(f"Invalid action type: {action}")
                return errors
            
            # Validate action parameters
            if "parameters" in step:
                param_rules = self._rules["sequences"]["actions"][action]
                
                # Check required parameters
                if "required_parameters" in param_rules:
                    errors.extend(self._check_required_fields(
                        parameters,
                        param_rules["required_parameters"],
                        f"Action {action}: "
                    ))
                
                # Check parameter values
                if "parameter_rules" in param_rules:
                    for param, rules in param_rules["parameter_rules"].items():
                        if param in parameters:
                            value = parameters[param]
                            
                            if "min" in rules or "max" in rules:
                                error = self._check_numeric_range(
                                    value,
                                    rules.get("min"),
                                    rules.get("max"),
                                    param
                                )
                                if error:
                                    errors.append(f"Action {action}: {error}")
                                    
                            if "enum" in rules:
                                error = self._check_enum_value(
                                    value,
                                    rules["enum"],
                                    param
                                )
                                if error:
                                    errors.append(f"Action {action}: {error}")
                
        except Exception as e:
            errors.append(f"Action step validation error: {str(e)}")
        return errors

    async def _validate_pattern_step(self, step: Dict[str, Any]) -> List[str]:
        """Validate pattern step.
        
        Args:
            step: Step data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            pattern = step["pattern"]
            
            # Check pattern exists
            if not await self._check_pattern_exists(pattern):
                errors.append(f"Pattern not found: {pattern}")
                return errors
            
            # Validate pattern modifications
            if "modifications" in step:
                mod_errors = await self._validate_pattern_modifications(
                    step["modifications"]
                )
                errors.extend(mod_errors)
                
        except Exception as e:
            errors.append(f"Pattern step validation error: {str(e)}")
        return errors

    def _validate_step_order(
        self,
        steps: List[Dict[str, Any]],
        required_order: List[str]
    ) -> List[str]:
        """Validate step order.
        
        Args:
            steps: Sequence steps
            required_order: Required step order
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            current_index = 0
            
            for required in required_order:
                # Find next matching step
                found = False
                for i in range(current_index, len(steps)):
                    step = steps[i]
                    if "action" in step and step["action"] == required:
                        current_index = i + 1
                        found = True
                        break
                
                if not found:
                    errors.append(f"Step order violation: {required} not found in expected position")
                    
        except Exception as e:
            errors.append(f"Step order validation error: {str(e)}")
        return errors

    async def _check_pattern_exists(self, pattern_id: str) -> bool:
        """Check if pattern exists.
        
        Args:
            pattern_id: Pattern ID to check
            
        Returns:
            Whether pattern exists
        """
        try:
            response = await self._message_broker.request(
                "pattern/exists",
                {"pattern_id": pattern_id}
            )
            return response.get("exists", False)
        except Exception:
            return False
