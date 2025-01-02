"""Pattern management endpoints."""

from fastapi import APIRouter, Depends, status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process import get_process_service
from micro_cold_spray.api.process.models.process_models import (
    BaseResponse,
    Pattern,
    PatternResponse,
    PatternListResponse
)

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get(
    "",
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


@router.post(
    "/generate",
    response_model=BaseResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation failed"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to generate pattern"}
    }
)
async def generate_pattern(
    pattern: Pattern,
    service: ProcessService = Depends(get_process_service)
) -> BaseResponse:
    """Generate new pattern."""
    try:
        pattern_id = await service.pattern_service.generate_pattern(pattern)
        return BaseResponse(message=f"Pattern {pattern_id} generated successfully")
    except Exception as e:
        logger.error(f"Failed to generate pattern: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to generate pattern: {str(e)}"
        )
