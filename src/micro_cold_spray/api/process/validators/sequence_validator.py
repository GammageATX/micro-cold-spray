"""Sequence validation for process API."""

from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.process.schemas import SequenceData


def validate_sequence(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate sequence data."""
    try:
        sequence_data = SequenceData(**data)
        return sequence_data.model_dump()
    except Exception as e:
        logger.error(f"Sequence validation failed: {e}")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=str(e)
        )
