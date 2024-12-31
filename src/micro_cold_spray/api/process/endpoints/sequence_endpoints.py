"""Sequence execution endpoints."""

from fastapi import APIRouter, Depends
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.models.process_models import (
    ExecutionStatus,
    SequenceResponse
)
from micro_cold_spray.api.process.endpoints.dependencies import get_service


router = APIRouter(prefix="/sequences", tags=["sequences"])


@router.post("/{sequence_id}/start")
async def start_sequence(
    sequence_id: str,
    service: ProcessService = Depends(get_service)
) -> SequenceResponse:
    """Start sequence execution."""
    try:
        status = await service.start_sequence(sequence_id)
        return SequenceResponse(
            message=f"Started sequence {sequence_id}",
            status=status
        )
    except Exception as e:
        logger.error(f"Failed to start sequence {sequence_id}: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to start sequence: {str(e)}"
        )


@router.post("/{sequence_id}/stop")
async def stop_sequence(
    sequence_id: str,
    service: ProcessService = Depends(get_service)
) -> SequenceResponse:
    """Stop sequence execution."""
    try:
        status = await service.stop_sequence(sequence_id)
        return SequenceResponse(
            message=f"Stopped sequence {sequence_id}",
            status=status
        )
    except Exception as e:
        logger.error(f"Failed to stop sequence {sequence_id}: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to stop sequence: {str(e)}"
        )


@router.get("/{sequence_id}/status")
async def get_sequence_status(
    sequence_id: str,
    service: ProcessService = Depends(get_service)
) -> SequenceResponse:
    """Get sequence execution status."""
    try:
        status = await service.get_sequence_status(sequence_id)
        return SequenceResponse(
            message=f"Status for sequence {sequence_id}: {status}",
            status=status
        )
    except Exception as e:
        logger.error(f"Failed to get sequence status {sequence_id}: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to get sequence status: {str(e)}"
        )
