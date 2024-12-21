"""FastAPI router for validation endpoints."""

from typing import Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, status
from pydantic import BaseModel
from loguru import logger

from micro_cold_spray.api.validation.validation_service import ValidationService
from micro_cold_spray.api.base.base_errors import create_error


class ValidationRequest(BaseModel):
    """Validation request model."""
    type: str
    data: Dict[str, Any]


class ValidationResponse(BaseModel):
    """Validation response model."""
    type: str
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    is_running: bool
    timestamp: datetime


# Create router
router = APIRouter(
    prefix="/validation",
    tags=["validation"]
)


def get_service() -> ValidationService:
    """Get validation service instance.
    
    Returns:
        ValidationService instance
        
    Raises:
        HTTPException: If service not initialized
    """
    if not hasattr(get_service, "_service"):
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Validation service not initialized"
        )
    return get_service._service


@router.post(
    "/validate",
    response_model=ValidationResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
    }
)
async def validate_data(
    request: ValidationRequest,
    background_tasks: BackgroundTasks,
    service: ValidationService = Depends(get_service)
) -> ValidationResponse:
    """Validate data against rules.
    
    Args:
        request: Validation request
        background_tasks: Background tasks
        service: Validation service
        
    Returns:
        Validation response
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        # Validate based on type
        result = None
        validation_type = request.type
        validation_data = request.data
        
        if validation_type == "parameters":
            result = await service.validate_parameters(validation_data)
        elif validation_type == "pattern":
            result = await service.validate_pattern(validation_data)
        elif validation_type == "sequence":
            result = await service.validate_sequence(validation_data)
        elif validation_type == "hardware":
            result = await service.validate_hardware(validation_data)
        else:
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Unknown validation type: {validation_type}"
            )

        # Log validation result
        if result["valid"]:
            background_tasks.add_task(
                logger.info,
                f"Validation passed for {validation_type}"
            )
        else:
            background_tasks.add_task(
                logger.warning,
                f"Validation failed for {validation_type}: {result['errors']}"
            )
            
        return ValidationResponse(
            type=validation_type,
            valid=result["valid"],
            errors=result.get("errors", []),
            warnings=result.get("warnings", []),
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Validation request failed: {e}")
        if isinstance(e, create_error):
            raise e
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"Validation failed: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
    }
)
async def health_check(service: ValidationService = Depends(get_service)) -> HealthResponse:
    """Check service health status.
    
    Args:
        service: Validation service
        
    Returns:
        Health check response
        
    Raises:
        HTTPException: If health check fails
    """
    try:
        return HealthResponse(
            status="ok" if service.is_running else "error",
            is_running=service.is_running,
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        if isinstance(e, create_error):
            raise e
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"Health check failed: {str(e)}"
        )
