"""Base validation functions."""

from typing import Any, Dict, List, Union
from datetime import datetime


def check_required_fields(data: Dict[str, Any], required_fields: List[str], message: str) -> List[str]:
    """Check if required fields are present.
    
    Args:
        data: Data to check
        required_fields: List of required field names
        message: Error message to use
        
    Returns:
        List of error messages
    """
    errors = []
    for field in required_fields:
        if field not in data:
            errors.append(f"{message} Missing required field: {field}")
    return errors


def check_unknown_fields(data: Dict[str, Any], allowed_fields: List[str], message: str) -> List[str]:
    """Check for unknown fields.
    
    Args:
        data: Data to check
        allowed_fields: List of allowed field names
        message: Warning message to use
        
    Returns:
        List of warning messages
    """
    warnings = []
    for field in data:
        if field not in allowed_fields:
            warnings.append(f"{message} Unknown field: {field}")
    return warnings


def check_numeric_range(
    value: Union[int, float],
    min_val: Union[int, float, None] = None,
    max_val: Union[int, float, None] = None,
    field_name: str = ""
) -> str:
    """Check if numeric value is within range.
    
    Args:
        value: Value to check
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        field_name: Name of field being checked
        
    Returns:
        Error message if validation fails, empty string otherwise
    """
    try:
        if min_val is not None and value < min_val:
            return f"{field_name} must be greater than or equal to {min_val}"
        if max_val is not None and value > max_val:
            return f"{field_name} must be less than or equal to {max_val}"
        return ""
    except Exception:
        return f"{field_name} must be a number"


def check_enum_value(value: Any, allowed_values: List[Any], field_name: str = "") -> str:
    """Check if value is in allowed values.
    
    Args:
        value: Value to check
        allowed_values: List of allowed values
        field_name: Name of field being checked
        
    Returns:
        Error message if validation fails, empty string otherwise
    """
    if value not in allowed_values:
        return f"{field_name} must be one of: {', '.join(str(v) for v in allowed_values)}"
    return ""


def check_timestamp(value: Any) -> str:
    """Check if value is a valid timestamp.
    
    Args:
        value: Value to check
        
    Returns:
        Error message if validation fails, empty string otherwise
    """
    try:
        if isinstance(value, str):
            datetime.fromisoformat(value.replace('Z', '+00:00'))
        elif isinstance(value, (int, float)):
            datetime.fromtimestamp(value)
        else:
            return "Timestamp must be a string in ISO format or a numeric timestamp"
        return ""
    except Exception:
        return "Invalid timestamp format"
