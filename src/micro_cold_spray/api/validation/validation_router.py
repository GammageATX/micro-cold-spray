"""FastAPI router for validation endpoints."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import APIRouter, HTTPException, BackgroundTasks, FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from micro_cold_spray.api.validation.validation_service import ValidationService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base import add_health_endpoints
from micro_cold_spray.api.config import get_config_service
from micro_cold_spray.api.messaging import MessagingService


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
        if not config_service.is_running:
            await config_service.start()
            if not config_service.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="ConfigService failed to start"
                )
            logger.info("ConfigService started successfully")
        
        # Create and start message broker
        message_broker = MessagingService(config_service=config_service)
        await message_broker.start()
        if not message_broker.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="MessageBroker failed to start"
            )
        logger.info("MessageBroker started successfully")
        
        # Initialize validation service
        _service = ValidationService(
            config_service=config_service,
            message_broker=message_broker
        )
        await _service.start()
        if not _service.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="ValidationService failed to start"
            )
        logger.info("ValidationService started successfully")
        
        # Add health endpoints
        add_health_endpoints(app, _service)
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


# Create FastAPI app with lifespan
app = FastAPI(title="Validation API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_service() -> ValidationService:
    """Get validation service instance."""
    if _service is None or not _service.is_running:
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="ValidationService not initialized"
        )
    return _service


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
        if isinstance(e, HTTPException):
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
        if isinstance(e, HTTPException):
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
            status=health["status"],
            service_name=service.name,
            version=getattr(service, "version", "1.0.0"),
            is_running=service.is_running,
            timestamp=datetime.now()
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Health check failed",
            context={"error": str(e)},
            cause=e
        )

# Include router in app
app.include_router(router)
