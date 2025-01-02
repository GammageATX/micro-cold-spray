"""Process API endpoints."""

from fastapi import APIRouter, Depends, status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.process import get_process_service, ProcessService
from micro_cold_spray.api.process.models.process_models import (
    NozzleResponse,
    NozzleListResponse,
    PowderResponse,
    PowderListResponse
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
        return await service.health()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=str(e)
        )


@router.get(
    "/nozzles",
    response_model=NozzleListResponse,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to list nozzles"}
    }
)
async def list_nozzles(
    service: ProcessService = Depends(get_process_service)
) -> NozzleListResponse:
    """List available nozzles."""
    try:
        nozzles = await service.parameter_service.list_nozzles()
        return NozzleListResponse(nozzles=nozzles)
    except Exception as e:
        logger.error(f"Failed to list nozzles: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to list nozzles: {str(e)}"
        )


@router.get(
    "/nozzles/{nozzle_id}",
    response_model=NozzleResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Nozzle not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to get nozzle"}
    }
)
async def get_nozzle(
    nozzle_id: str,
    service: ProcessService = Depends(get_process_service)
) -> NozzleResponse:
    """Get nozzle by ID."""
    try:
        nozzle = await service.parameter_service.get_nozzle(nozzle_id)
        return NozzleResponse(nozzle=nozzle)
    except Exception as e:
        logger.error(f"Failed to get nozzle {nozzle_id}: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to get nozzle: {str(e)}"
        )


@router.get(
    "/powders",
    response_model=PowderListResponse,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to list powders"}
    }
)
async def list_powders(
    service: ProcessService = Depends(get_process_service)
) -> PowderListResponse:
    """List available powders."""
    try:
        powders = await service.parameter_service.list_powders()
        return PowderListResponse(powders=powders)
    except Exception as e:
        logger.error(f"Failed to list powders: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to list powders: {str(e)}"
        )


@router.get(
    "/powders/{powder_id}",
    response_model=PowderResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Powder not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to get powder"}
    }
)
async def get_powder(
    powder_id: str,
    service: ProcessService = Depends(get_process_service)
) -> PowderResponse:
    """Get powder by ID."""
    try:
        powder = await service.parameter_service.get_powder(powder_id)
        return PowderResponse(powder=powder)
    except Exception as e:
        logger.error(f"Failed to get powder {powder_id}: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to get powder: {str(e)}"
        )
