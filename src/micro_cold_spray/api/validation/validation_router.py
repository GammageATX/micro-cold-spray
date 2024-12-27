"""Validation router."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.validation.validation_service import ValidationService


router = APIRouter(
    prefix="/validation",
    tags=["validation"]
)


async def get_service() -> ValidationService:
    """Get validation service instance.
    
    Returns:
        ValidationService: Validation service instance
    """
    return router.state.service


@router.post("/hardware")
async def validate_hardware(
    data: Dict[str, Any],
    service: ValidationService = Depends(get_service)
) -> Dict[str, Any]:
    """Validate hardware configuration.
    
    Args:
        data: Hardware configuration to validate
        service: Validation service instance
        
    Returns:
        Dict containing:
            - valid: Whether validation passed
            - errors: List of error messages
            - warnings: List of warning messages
    """
    try:
        return await service.validate_hardware(data)
    except Exception as e:
        logger.error(f"Hardware validation failed: {e}")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"Hardware validation failed: {str(e)}"
        )


@router.post("/parameter/{parameter_type}")
async def validate_parameter(
    parameter_type: str,
    data: Dict[str, Any],
    service: ValidationService = Depends(get_service)
) -> Dict[str, Any]:
    """Validate parameter configuration.
    
    Args:
        parameter_type: Type of parameter to validate
        data: Parameter configuration to validate
        service: Validation service instance
        
    Returns:
        Dict containing:
            - valid: Whether validation passed
            - errors: List of error messages
            - warnings: List of warning messages
    """
    try:
        return await service.validate_parameter(parameter_type, data)
    except Exception as e:
        logger.error(f"Parameter validation failed: {e}")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"Parameter validation failed: {str(e)}"
        )


@router.post("/pattern/{pattern_type}")
async def validate_pattern(
    pattern_type: str,
    data: Dict[str, Any],
    service: ValidationService = Depends(get_service)
) -> Dict[str, Any]:
    """Validate pattern configuration.
    
    Args:
        pattern_type: Type of pattern to validate
        data: Pattern configuration to validate
        service: Validation service instance
        
    Returns:
        Dict containing:
            - valid: Whether validation passed
            - errors: List of error messages
            - warnings: List of warning messages
    """
    try:
        return await service.validate_pattern(pattern_type, data)
    except Exception as e:
        logger.error(f"Pattern validation failed: {e}")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"Pattern validation failed: {str(e)}"
        )


@router.post("/sequence")
async def validate_sequence(
    data: Dict[str, Any],
    service: ValidationService = Depends(get_service)
) -> Dict[str, Any]:
    """Validate sequence configuration.
    
    Args:
        data: Sequence configuration to validate
        service: Validation service instance
        
    Returns:
        Dict containing:
            - valid: Whether validation passed
            - errors: List of error messages
            - warnings: List of warning messages
    """
    try:
        return await service.validate_sequence(data)
    except Exception as e:
        logger.error(f"Sequence validation failed: {e}")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"Sequence validation failed: {str(e)}"
        )
