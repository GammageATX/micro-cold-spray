"""List endpoints for process API."""

from fastapi import Depends
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.models.process_models import (
    PatternListResponse,
    ParameterSetListResponse
)
from micro_cold_spray.api.process.endpoints.dependencies import get_service


async def list_patterns(service: ProcessService = Depends(get_service)) -> PatternListResponse:
    """List available patterns."""
    patterns = await service._pattern.list_patterns()
    return PatternListResponse(
        message=f"Retrieved {len(patterns)} patterns",
        patterns=patterns
    )


async def list_parameter_sets(service: ProcessService = Depends(get_service)) -> ParameterSetListResponse:
    """List available parameter sets."""
    parameter_sets = await service._parameter.list_parameter_sets()
    return ParameterSetListResponse(
        message=f"Retrieved {len(parameter_sets)} parameter sets",
        parameter_sets=parameter_sets
    )
