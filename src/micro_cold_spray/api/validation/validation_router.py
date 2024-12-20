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


class ValidationRulesResponse(BaseModel):
    """Validation rules response model."""
    type: str
    rules: Dict[str, Any]
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service_name: str
    version: str
    is_running: bool
    timestamp: datetime


# Create router
router = APIRouter(tags=["validation"])


def get_service() -> ValidationService:
    """Get validation service instance."""
    if not hasattr(get_service, "_service"):
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="ValidationService not initialized"
        )
    return get_service._service


@router.post(
    "/validate",
    response_model=ValidationResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request format or validation error"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
    }
)
async def validate_data(
    request: ValidationRequest,
    background_tasks: BackgroundTasks,
    service: ValidationService = Depends(get_service)
) -> ValidationResponse:
    """Validate data against rules."""
    try:
        # Perform validation based on type
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
                message="Unknown validation type",
                context={"type": validation_type}
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
        if isinstance(e, create_error):
            raise e
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Validation failed",
            context={"error": str(e)},
            cause=e
        )


@router.get(
    "/rules/{rule_type}",
    response_model=ValidationRulesResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid rule type"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
    }
)
async def get_validation_rules(
    rule_type: str,
    service: ValidationService = Depends(get_service)
) -> ValidationRulesResponse:
    """Get validation rules for type."""
    try:
        rules = await service.get_rules(rule_type)
        return ValidationRulesResponse(
            type=rule_type,
            rules=rules,
            timestamp=datetime.now()
        )
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to get validation rules",
            context={"error": str(e)},
            cause=e
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
    }
)
async def health_check(service: ValidationService = Depends(get_service)) -> HealthResponse:
    """Check API and service health status."""
    try:
        health = await service.check_health()
        return HealthResponse(
            status="ok" if health["is_healthy"] else "error",
            service_name=service.name,
            version="1.0.0",
            is_running=service.is_running,
            timestamp=datetime.now()
        )
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Health check failed",
            context={"error": str(e)},
            cause=e
        )
