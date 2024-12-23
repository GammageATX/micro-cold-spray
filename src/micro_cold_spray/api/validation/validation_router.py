"""FastAPI router for validation endpoints."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from pydantic import BaseModel, Field
from loguru import logger

from micro_cold_spray.api.validation.validation_service import ValidationService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.ui.utils import get_uptime, get_memory_usage


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
    status: str = Field(..., description="Service status (ok or error)")
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    is_running: bool = Field(..., description="Whether service is running")
    uptime: float = Field(..., description="Service uptime in seconds")
    memory_usage: Dict[str, float] = Field(..., description="Memory usage stats")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


# Create router
router = APIRouter()


def get_validation_service(request: Request) -> ValidationService:
    """Get validation service from app state."""
    if not hasattr(request.app.state, "validation_service"):
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Validation service not initialized"
        )
    return request.app.state.validation_service


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
    service: ValidationService = Depends(get_validation_service)
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
async def health_check(
    service: ValidationService = Depends(get_validation_service)
) -> HealthResponse:
    """Check service health status."""
    try:
        return HealthResponse(
            status="ok" if service.is_running else "error",
            service_name=service.name,
            version=service.version,
            is_running=service.is_running,
            uptime=get_uptime(),
            memory_usage=get_memory_usage(),
            error=None if service.is_running else "Service not running",
            timestamp=datetime.now()
        )
    except Exception as e:
        error_msg = f"Health check failed: {str(e)}"
        logger.error(error_msg)
        return HealthResponse(
            status="error",
            service_name=getattr(service, "name", "validation"),
            version=getattr(service, "version", "1.0.0"),
            is_running=False,
            uptime=0.0,
            memory_usage={},
            error=error_msg,
            timestamp=datetime.now()
        )
