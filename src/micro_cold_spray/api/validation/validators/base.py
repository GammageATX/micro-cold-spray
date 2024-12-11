"""Base validator class."""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from ...messaging import MessagingService
from ..exceptions import ValidationError


class BaseValidator(ABC):
    """Base class for validators."""

    def __init__(
        self,
        validation_rules: Dict[str, Any],
        message_broker: Optional[MessagingService] = None
    ):
        """Initialize validator.
        
        Args:
            validation_rules: Validation rules from config
            message_broker: Optional message broker for hardware checks
        """
        self._rules = validation_rules
        self._message_broker = message_broker

    @abstractmethod
    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against rules.
        
        Args:
            data: Data to validate
            
        Returns:
            Dict containing:
                - valid: Whether validation passed
                - errors: List of error messages
                - warnings: List of warning messages
                
        Raises:
            ValidationError: If validation fails
        """
        pass

    async def _get_tag_value(self, tag: str) -> Any:
        """Get tag value from Communication API.
        
        Args:
            tag: Tag to get value for
            
        Returns:
            Tag value
            
        Raises:
            ValidationError: If tag value cannot be retrieved
        """
        if not self._message_broker:
            raise ValidationError("Message broker not available")
            
        try:
            response = await self._message_broker.request(
                "tag/request",
                {"tag": tag}
            )
            return response["value"]
        except Exception as e:
            raise ValidationError(f"Failed to get tag value: {tag}", {"error": str(e)})

    def _check_required_fields(
        self,
        data: Dict[str, Any],
        required_fields: List[str],
        prefix: str = ""
    ) -> List[str]:
        """Check required fields are present.
        
        Args:
            data: Data to check
            required_fields: List of required field names
            prefix: Optional prefix for error messages
            
        Returns:
            List of error messages
        """
        errors = []
        for field in required_fields:
            if field not in data:
                errors.append(f"{prefix}Missing required field: {field}")
        return errors

    def _check_unknown_fields(
        self,
        data: Dict[str, Any],
        valid_fields: List[str],
        prefix: str = ""
    ) -> List[str]:
        """Check for unknown fields.
        
        Args:
            data: Data to check
            valid_fields: List of valid field names
            prefix: Optional prefix for error messages
            
        Returns:
            List of error messages
        """
        errors = []
        for field in data:
            if field not in valid_fields:
                errors.append(f"{prefix}Unknown field: {field}")
        return errors

    def _check_numeric_range(
        self,
        value: float,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        field_name: str = "Value"
    ) -> Optional[str]:
        """Check numeric value is within range.
        
        Args:
            value: Value to check
            min_val: Optional minimum value
            max_val: Optional maximum value
            field_name: Name of field for error message
            
        Returns:
            Error message if validation fails, None otherwise
        """
        if min_val is not None and value < min_val:
            return f"{field_name} {value} below minimum: {min_val}"
        if max_val is not None and value > max_val:
            return f"{field_name} {value} above maximum: {max_val}"
        return None

    def _check_enum_value(
        self,
        value: Any,
        valid_values: List[Any],
        field_name: str = "Value"
    ) -> Optional[str]:
        """Check value is in enumerated list.
        
        Args:
            value: Value to check
            valid_values: List of valid values
            field_name: Name of field for error message
            
        Returns:
            Error message if validation fails, None otherwise
        """
        if value not in valid_values:
            return f"{field_name} must be one of: {valid_values}"
        return None
