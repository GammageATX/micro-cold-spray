"""Validation router."""

from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.monitoring import get_uptime
from micro_cold_spray.api.validation.validation_service import ValidationService


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status (ok or error)")
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Service uptime in seconds")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


router = APIRouter(
    prefix="/api/validation",
    tags=["validation"]
)

validation_service = ValidationService()


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
    }
)
async def health_check() -> HealthResponse:
    """Check service health status."""
    try:
        return HealthResponse(
            status="ok",
            service_name="validation",
            version="1.0.0",
            uptime=get_uptime(),
            error=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        error_msg = f"Health check failed: {str(e)}"
        logger.error(error_msg)
        return HealthResponse(
            status="error",
            service_name="validation",
            version="1.0.0",
            uptime=0.0,
            error=error_msg,
            timestamp=datetime.now()
        )


@router.post("/hardware")
async def validate_hardware(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate hardware configuration.
    
    Args:
        data: Hardware configuration to validate
        
    Returns:
        Dict containing:
            - valid: Whether validation passed
            - errors: List of error messages
            - warnings: List of warning messages
    """
    try:
        return await validation_service.validate_hardware(data)
    except Exception as e:
        logger.error(f"Hardware validation failed: {e}")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"Hardware validation failed: {str(e)}"
        )


@router.post("/parameter/{parameter_type}")
async def validate_parameter(parameter_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parameter configuration.
    
    Args:
        parameter_type: Type of parameter to validate
        data: Parameter configuration to validate
        
    Returns:
        Dict containing:
            - valid: Whether validation passed
            - errors: List of error messages
            - warnings: List of warning messages
    """
    try:
        return await validation_service.validate_parameter(parameter_type, data)
    except Exception as e:
        logger.error(f"Parameter validation failed: {e}")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"Parameter validation failed: {str(e)}"
        )


@router.post("/pattern/{pattern_type}")
async def validate_pattern(pattern_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate pattern configuration.
    
    Args:
        pattern_type: Type of pattern to validate
        data: Pattern configuration to validate
        
    Returns:
        Dict containing:
            - valid: Whether validation passed
            - errors: List of error messages
            - warnings: List of warning messages
    """
    try:
        return await validation_service.validate_pattern(pattern_type, data)
    except Exception as e:
        logger.error(f"Pattern validation failed: {e}")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"Pattern validation failed: {str(e)}"
        )


@router.post("/sequence")
async def validate_sequence(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate sequence configuration.
    
    Args:
        data: Sequence configuration to validate
        
    Returns:
        Dict containing:
            - valid: Whether validation passed
            - errors: List of error messages
            - warnings: List of warning messages
    """
    try:
        return await validation_service.validate_sequence(data)
    except Exception as e:
        logger.error(f"Sequence validation failed: {e}")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"Sequence validation failed: {str(e)}"
        )
