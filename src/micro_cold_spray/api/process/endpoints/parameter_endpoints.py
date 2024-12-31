"""Parameter management endpoints."""

from fastapi import APIRouter, Depends, status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.dependencies import get_process_service
from micro_cold_spray.api.process.models.process_models import (
    ParameterRequest,
    ParameterSetListResponse,
    MessageResponse
)

router = APIRouter(prefix="/parameters", tags=["parameters"])


@router.get(
    "",
    response_model=ParameterSetListResponse,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to list parameter sets"}
    }
)
async def list_parameters(
    service: ProcessService = Depends(get_process_service)
) -> ParameterSetListResponse:
    """List available parameter sets."""
    try:
        params = await service.parameter_service.list_parameters()
        return ParameterSetListResponse(parameter_sets=params)
    except Exception as e:
        logger.error(f"Failed to list parameter sets: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to list parameter sets: {str(e)}"
        )


@router.post(
    "/generate",
    response_model=MessageResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation failed"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to generate parameter set"}
    }
)
async def generate_parameter_set(
    parameter: ParameterRequest,
    service: ProcessService = Depends(get_process_service)
) -> MessageResponse:
    """Generate new parameter set."""
    try:
        param_id = await service.parameter_service.generate_parameter(parameter)
        return MessageResponse(message=f"Parameter set {param_id} generated successfully")
    except Exception as e:
        logger.error(f"Failed to generate parameter set: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to generate parameter set: {str(e)}"
        )


@router.get(
    "/{param_id}",
    response_model=ParameterRequest,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Parameter set not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to get parameter set"}
    }
)
async def get_parameter_set(
    param_id: str,
    service: ProcessService = Depends(get_process_service)
) -> ParameterRequest:
    """Get parameter set by ID."""
    try:
        return await service.parameter_service.get_parameter(param_id)
    except Exception as e:
        logger.error(f"Failed to get parameter set {param_id}: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to get parameter set: {str(e)}"
        )


@router.put(
    "/{param_id}",
    response_model=MessageResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Parameter set not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation failed"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to update parameter set"}
    }
)
async def update_parameter_set(
    param_id: str,
    parameter: ParameterRequest,
    service: ProcessService = Depends(get_process_service)
) -> MessageResponse:
    """Update parameter set."""
    try:
        await service.parameter_service.update_parameter(param_id, parameter)
        return MessageResponse(message=f"Parameter set {param_id} updated successfully")
    except Exception as e:
        logger.error(f"Failed to update parameter set {param_id}: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to update parameter set: {str(e)}"
        )
