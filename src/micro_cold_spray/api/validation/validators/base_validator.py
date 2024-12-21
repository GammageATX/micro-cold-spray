"""Validation utility functions."""

from typing import Dict, Any, List, Optional, Union, Pattern
import re
from datetime import datetime
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.messaging import MessagingService


async def get_tag_value(message_broker: MessagingService, tag: str) -> Any:
    """Get tag value from Communication API.
    
    Args:
        message_broker: Message broker service
        tag: Tag to get value for
        
    Returns:
        Tag value
        
    Raises:
        HTTPException: If tag value cannot be retrieved
    """
    if not message_broker:
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Message broker not available"
        )
        
    try:
        response = await message_broker.request(
            "tag/request",
            {"tag": tag}
        )
        return response["value"]
    except Exception as e:
        logger.error(f"Failed to get tag value {tag}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"Failed to get tag value: {str(e)}"
        )


def check_required_fields(
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
    errors: List[str] = []
    for field in required_fields:
        if field not in data:
            errors.append(f"{prefix}Missing required field: {field}")
        elif data[field] is None:
            errors.append(f"{prefix}Field cannot be null: {field}")
    return errors


def check_unknown_fields(
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
    errors: List[str] = []
    for field in data:
        if field not in valid_fields:
            errors.append(f"{prefix}Unknown field: {field}")
    return errors


def check_numeric_range(
    value: Union[int, float, str],
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
    try:
        num_value = float(value)
        if min_val is not None and num_value < min_val:
            return f"{field_name} {value} below minimum: {min_val}"
        if max_val is not None and num_value > max_val:
            return f"{field_name} {value} above maximum: {max_val}"
        return None
    except (TypeError, ValueError):
        return f"{field_name} must be numeric"


def check_enum_value(
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


def check_pattern(
    value: str,
    pattern: Union[str, Pattern[str]],
    field_name: str = "Value"
) -> Optional[str]:
    """Check string matches pattern.
    
    Args:
        value: String to check
        pattern: Regex pattern to match
        field_name: Name of field for error message
        
    Returns:
        Error message if validation fails, None otherwise
    """
    try:
        if not isinstance(value, str):
            return f"{field_name} must be string"
            
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
            
        if not pattern.match(value):
            return f"{field_name} does not match pattern: {pattern.pattern}"
            
        return None
        
    except Exception as e:
        logger.error(f"Pattern check failed: {str(e)}")
        return f"Invalid pattern check: {str(e)}"


def check_timestamp(
    value: Union[str, datetime],
    field_name: str = "Timestamp"
) -> Optional[str]:
    """Check timestamp is valid.
    
    Args:
        value: Timestamp to check
        field_name: Name of field for error message
        
    Returns:
        Error message if validation fails, None otherwise
    """
    try:
        if isinstance(value, str):
            datetime.fromisoformat(value)
        elif not isinstance(value, datetime):
            return f"{field_name} must be ISO format string or datetime"
        return None
    except ValueError:
        return f"{field_name} must be valid ISO format"
