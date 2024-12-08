"""Process validation component."""
from typing import Any, Dict, List, Optional, Tuple

from ....exceptions import ValidationError
from ....infrastructure.config.config_manager import ConfigManager
from ....infrastructure.messaging.message_broker import MessageBroker


class ProcessValidator:
    """Validates process operations and parameters."""

    def __init__(
            self,
            message_broker: MessageBroker,
            config_manager: ConfigManager):
        """Initialize process validator.

        Args:
            message_broker: MessageBroker instance for communication
            config_manager: ConfigManager instance for configuration
        """
        self._message_broker = message_broker
        self._config = config_manager
        self._process_config = {}

    async def initialize(self) -> None:
        """Load configuration and initialize validator."""
        config = await self._config.get_config('process')
        self._process_config = config['process']

    async def validate_action(
            self,
            action_name: str,
            parameters: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate action parameters against defined requirements.

        Args:
            action_name: Name of the action to validate
            parameters: Action parameters to validate

        Returns:
            Tuple of (valid: bool, errors: List[str])
        """
        errors = []

        try:
            # Get action definition
            action_def = self._get_action_definition(action_name)
            if not action_def:
                errors.append(f"Unknown action: {action_name}")
                return False, errors

            # Validate required parameters
            if 'requires' in action_def:
                for param_name, param_type in action_def['requires'].items():
                    if param_name not in parameters:
                        errors.append(
                            f"Missing required parameter: {param_name}")
                    else:
                        # Type validation
                        value = parameters[param_name]
                        if not self._validate_parameter_type(
                                value, param_type):
                            errors.append(
                                f"Invalid type for {param_name}: expected {param_type}")

            # Validate parameter ranges if defined
            if 'parameters' in action_def:
                for param_name, param_def in action_def['parameters'].items():
                    if param_name in parameters:
                        value = parameters[param_name]
                        param_errors = self._validate_parameter_value(
                            value, param_def)
                        errors.extend(param_errors)

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return len(errors) == 0, errors

    async def validate_pattern(
            self,
            pattern_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate pattern definition and parameters.

        Args:
            pattern_data: Pattern definition to validate

        Returns:
            Tuple of (valid: bool, errors: List[str])
        """
        errors = []

        try:
            # Validate required pattern fields
            required_fields = ['type', 'parameters']
            for field in required_fields:
                if field not in pattern_data:
                    errors.append(f"Missing required field: {field}")
                    return False, errors

            # Get pattern type definition
            pattern_type = pattern_data['type']
            type_def = self._get_pattern_definition(pattern_type)
            if not type_def:
                errors.append(f"Unknown pattern type: {pattern_type}")
                return False, errors

            # Validate pattern parameters
            params = pattern_data.get('parameters', {})
            for param_name, param_def in type_def['parameters'].items():
                if param_name not in params:
                    if param_def.get('required', True):
                        errors.append(
                            f"Missing required parameter: {param_name}")
                else:
                    value = params[param_name]
                    param_errors = self._validate_parameter_value(
                        value, param_def)
                    errors.extend(param_errors)

            # Validate pattern bounds
            if 'bounds' in pattern_data:
                bounds_errors = self._validate_pattern_bounds(
                    pattern_data['bounds'])
                errors.extend(bounds_errors)

        except Exception as e:
            errors.append(f"Pattern validation error: {str(e)}")

        return len(errors) == 0, errors

    async def validate_sequence(
            self,
            sequence_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate sequence definition and steps.

        Args:
            sequence_data: Sequence definition to validate

        Returns:
            Tuple of (valid: bool, errors: List[str])
        """
        errors = []

        try:
            # Validate required sequence fields
            required_fields = ['name', 'steps']
            for field in required_fields:
                if field not in sequence_data:
                    errors.append(f"Missing required field: {field}")
                    return False, errors

            # Validate each step
            for i, step in enumerate(sequence_data['steps']):
                step_errors = await self._validate_sequence_step(step)
                if step_errors:
                    errors.extend(
                        [f"Step {i+1}: {error}" for error in step_errors])

        except Exception as e:
            errors.append(f"Sequence validation error: {str(e)}")

        return len(errors) == 0, errors

    def _get_action_definition(self, action_name: str) -> Optional[Dict[str, Any]]:
        """Get action definition from config.

        Args:
            action_name: Name of the action

        Returns:
            Action definition dictionary or None if not found
        """
        actions = self._process_config.get('atomic_actions', {})
        parts = action_name.split('.')
        current = actions
        for part in parts:
            if part not in current:
                return None
            current = current[part]
        return current

    def _get_pattern_definition(self, pattern_type: str) -> Optional[Dict[str, Any]]:
        """Get pattern type definition from config.

        Args:
            pattern_type: Type of pattern

        Returns:
            Pattern type definition dictionary or None if not found
        """
        patterns = self._process_config.get('patterns', {})
        return patterns.get(pattern_type)

    def _validate_parameter_type(self, value: Any, expected_type: str) -> bool:
        """Validate parameter type.

        Args:
            value: Parameter value to validate
            expected_type: Expected parameter type

        Returns:
            True if type is valid, False otherwise
        """
        type_map = {
            'string': str,
            'integer': int,
            'float': float,
            'boolean': bool,
            'list': list,
            'dict': dict
        }

        expected = type_map.get(expected_type)
        if not expected:
            return True  # Skip validation for unknown types

        return isinstance(value, expected)

    def _validate_parameter_value(
            self,
            value: Any,
            param_def: Dict[str, Any]) -> List[str]:
        """Validate parameter value against its definition.

        Args:
            value: Parameter value to validate
            param_def: Parameter definition

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Type validation
            if 'type' in param_def:
                if not self._validate_parameter_type(value, param_def['type']):
                    errors.append(
                        f"Invalid type: expected {param_def['type']}")
                    return errors

            # Numeric range validation
            if isinstance(value, (int, float)):
                if 'min' in param_def and value < param_def['min']:
                    errors.append(
                        f"Value {value} below minimum {param_def['min']}")
                if 'max' in param_def and value > param_def['max']:
                    errors.append(
                        f"Value {value} above maximum {param_def['max']}")

            # Enum validation
            if 'enum' in param_def and value not in param_def['enum']:
                errors.append(
                    f"Value {value} not in allowed values: {param_def['enum']}")

        except Exception as e:
            errors.append(f"Parameter validation error: {str(e)}")

        return errors

    def _validate_pattern_bounds(self, bounds: Dict[str, Any]) -> List[str]:
        """Validate pattern bounds.

        Args:
            bounds: Pattern bounds to validate

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Validate required bounds fields
            required_fields = ['x_min', 'x_max', 'y_min', 'y_max']
            for field in required_fields:
                if field not in bounds:
                    errors.append(f"Missing required bound: {field}")
                    continue

                value = bounds[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"Invalid bound type for {field}")

            # Validate bound relationships
            if 'x_min' in bounds and 'x_max' in bounds:
                if bounds['x_min'] >= bounds['x_max']:
                    errors.append("x_min must be less than x_max")

            if 'y_min' in bounds and 'y_max' in bounds:
                if bounds['y_min'] >= bounds['y_max']:
                    errors.append("y_min must be less than y_max")

        except Exception as e:
            errors.append(f"Bounds validation error: {str(e)}")

        return errors

    async def _validate_sequence_step(self, step: Dict[str, Any]) -> List[str]:
        """Validate a single sequence step.

        Args:
            step: Step definition to validate

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Check step has exactly one key (action, validation, or time_delay)
            valid_keys = {'action', 'validation', 'time_delay', 'repeat'}
            step_keys = set(step.keys()) - {'parameters'}
            if len(step_keys) != 1:
                errors.append(
                    f"Step must have exactly one type key {valid_keys}")
                return errors

            step_type = step_keys.pop()
            if step_type not in valid_keys:
                errors.append(f"Invalid step type: {step_type}")
                return errors

            # Validate based on step type
            if step_type == 'action':
                action_name = step['action']
                parameters = step.get('parameters', {})
                valid, action_errors = await self.validate_action(
                    action_name, parameters)
                errors.extend(action_errors)

            elif step_type == 'validation':
                # Validation steps just need to exist in config
                validation_name = step['validation']
                if not self._validation_exists(validation_name):
                    errors.append(f"Unknown validation: {validation_name}")

            elif step_type == 'repeat':
                if 'count' not in step['repeat']:
                    errors.append("Repeat step missing count")
                if 'steps' not in step['repeat']:
                    errors.append("Repeat step missing steps")
                else:
                    # Validate nested steps
                    for nested_step in step['repeat']['steps']:
                        nested_errors = await self._validate_sequence_step(
                            nested_step)
                        errors.extend(nested_errors)

        except Exception as e:
            errors.append(f"Step validation error: {str(e)}")

        return errors

    def _validation_exists(self, validation_name: str) -> bool:
        """Check if validation rule exists in config.

        Args:
            validation_name: Name of validation rule

        Returns:
            True if validation exists, False otherwise
        """
        validations = self._process_config.get('validation', {})
        return validation_name in validations
