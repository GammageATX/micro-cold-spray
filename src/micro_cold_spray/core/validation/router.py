"""FastAPI router for validation endpoints."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import APIRouter, HTTPException, BackgroundTasks, FastAPI, Depends, status
from pydantic import BaseModel
from loguru import logger

from micro_cold_spray.core.validation.services.service import ValidationService
from micro_cold_spray.core.errors.exceptions import ValidationError, ServiceError
from micro_cold_spray.core.errors.codes import AppErrorCode, format_error
from micro_cold_spray.core.config.utils.singleton import get_config_service
from micro_cold_spray.core.messaging.services.service import MessagingService
from micro_cold_spray.core.base import create_service_dependency


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


# Create router without prefix (app already handles the /validation prefix)
router = APIRouter(tags=["validation"])
_service: Optional[ValidationService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global _service
    try:
        # Get shared config service instance
        config_service = get_config_service()
        await config_service.start()
        logger.info("ConfigService started successfully")
        
        # Create and start message broker
        message_broker = MessagingService(config_service=config_service)
        await message_broker.start()
        logger.info("MessageBroker started successfully")
        
        # Initialize validation service
        _service = ValidationService(
            config_service=config_service,
            message_broker=message_broker
        )
        await _service.start()
        logger.info("ValidationService started successfully")
        
        # Mount router to app
        app.include_router(router)
        logger.info("Validation router initialized")
        
        yield
        
        # Cleanup on shutdown
        logger.info("Validation API shutting down")
        if _service:
            try:
                await _service.stop()
                logger.info("Validation service stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping validation service: {e}")
            finally:
                _service = None
            
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Attempt cleanup
        if _service and _service.is_running:
            await _service.stop()
            _service = None
        raise


# Create dependency for ValidationService
get_validation_service = create_service_dependency(ValidationService)


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
    service: ValidationService = Depends(get_validation_service)
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=format_error(AppErrorCode.INVALID_ACTION, f"Unknown validation type: {validation_type}")
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
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=format_error(AppErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
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
    service: ValidationService = Depends(get_validation_service)
) -> ValidationRulesResponse:
    """Get validation rules for type."""
    try:
        rules = await service.get_rules(rule_type)
        return ValidationRulesResponse(
            type=rule_type,
            rules=rules,
            timestamp=datetime.now()
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=format_error(AppErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )
