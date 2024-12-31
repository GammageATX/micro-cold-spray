"""Pattern validation for process API."""

from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.process.schemas import PatternData


def validate_pattern(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate pattern data."""
    try:
        pattern_data = PatternData(**data)
        return pattern_data.model_dump()
    except Exception as e:
        logger.error(f"Pattern validation failed: {e}")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=str(e)
        )
