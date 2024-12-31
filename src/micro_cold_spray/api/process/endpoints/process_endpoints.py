"""Process API endpoints."""

from fastapi import APIRouter, Depends, Request, status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.dependencies import get_process_service
from micro_cold_spray.api.process.models.process_models import (
    PatternListResponse,
    ParameterSetListResponse,
    MessageResponse
)

router = APIRouter(prefix="/process", tags=["process"])


@router.get(
    "/health",
    response_model=ServiceHealth,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service not available"}
    }
)
async def health(
    service: ProcessService = Depends(get_process_service)
) -> ServiceHealth:
    """Get service health status."""
    try:
        return await service.get_health()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=str(e)
        )


@router.get(
    "/patterns",
    response_model=PatternListResponse,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to list patterns"}
    }
)
async def list_patterns(
    service: ProcessService = Depends(get_process_service)
) -> PatternListResponse:
    """List available patterns."""
    try:
        patterns = await service.pattern_service.list_patterns()
        return PatternListResponse(patterns=patterns)
    except Exception as e:
        logger.error(f"Failed to list patterns: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to list patterns: {str(e)}"
        )
