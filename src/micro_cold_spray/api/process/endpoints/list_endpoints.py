"""List endpoints for process API."""

from fastapi import Depends
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.models.process_models import (
    PatternListResponse,
    ParameterSetListResponse,
    SequenceListResponse,
    NozzleListResponse,
    PowderListResponse
)
from micro_cold_spray.api.process.endpoints.dependencies import get_service


async def list_patterns(service: ProcessService = Depends(get_service)) -> PatternListResponse:
    """List available patterns."""
    patterns = await service._pattern.list_patterns()
    return PatternListResponse(
        message=f"Retrieved {len(patterns)} patterns",
        patterns=patterns
    )


async def list_parameters(service: ProcessService = Depends(get_service)) -> ParameterSetListResponse:
    """List available parameters."""
    parameter_sets = await service._parameter.list_parameter_sets()
    return ParameterSetListResponse(
        message=f"Retrieved {len(parameter_sets)} parameter sets",
        parameter_sets=parameter_sets
    )


async def list_sequences(service: ProcessService = Depends(get_service)) -> SequenceListResponse:
    """List available sequences."""
    sequences = await service._sequence.list_sequences()
    return SequenceListResponse(
        message=f"Retrieved {len(sequences)} sequences",
        sequences=sequences
    )


async def list_nozzles(service: ProcessService = Depends(get_service)) -> NozzleListResponse:
    """List available nozzles."""
    nozzles = await service._parameter.list_nozzles()
    return NozzleListResponse(
        message=f"Retrieved {len(nozzles)} nozzles",
        nozzles=nozzles
    )


async def list_powders(service: ProcessService = Depends(get_service)) -> PowderListResponse:
    """List available powders."""
    powders = await service._parameter.list_powders()
    return PowderListResponse(
        message=f"Retrieved {len(powders)} powders",
        powders=powders
    )
