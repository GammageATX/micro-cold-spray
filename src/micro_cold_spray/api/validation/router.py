"""FastAPI router for validation endpoints."""

from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import APIRouter, HTTPException, BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .service import ValidationService
from .exceptions import ValidationError
from ..base.router import add_health_endpoints
from ..base.errors import ErrorCode, format_error
from ..config.singleton import get_config_service
from ..messaging.service import MessagingService

# Create router without prefix (app already handles the /validation prefix)
router = APIRouter(tags=["validation"])
_service: Optional[ValidationService] = None


async def init_router(app: FastAPI) -> None:
    """Initialize validation router with required services.
    
    Args:
        app: FastAPI application instance
    """
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
        
        # Add health endpoints
        add_health_endpoints(app, _service)
        # Mount router to app
        app.include_router(router)
        logger.info("Validation router initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize validation router: {e}")
        # Attempt cleanup
        if _service and _service.is_running:
            await _service.stop()
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    try:
        await init_router(app)
        yield
        
        # Cleanup on shutdown
        logger.info("Validation API shutting down")
        if _service:
            try:
                await _service.stop()
                logger.info("Validation service stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping validation service: {e}")
            
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Attempt cleanup
        if _service and _service.is_running:
            await _service.stop()
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
    if _service is None:
        error = ErrorCode.SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, "Validation service not initialized")
        )
    return _service


@router.post("/validate", response_model=Dict[str, Any])
async def validate_data(
    request: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Validate data against rules."""
    service = get_service()
    
    try:
        # Validate request format
        if "type" not in request:
            error = ErrorCode.VALIDATION_ERROR
            raise HTTPException(
                status_code=error.get_status_code(),
                detail=format_error(error, "Missing validation type")
            )
        if "data" not in request:
            error = ErrorCode.VALIDATION_ERROR
            raise HTTPException(
                status_code=error.get_status_code(),
                detail=format_error(error, "Missing validation data")
            )
            
        # Perform validation based on type
        validation_type = request["type"]
        validation_data = request["data"]
        
        if validation_type == "parameters":
            result = await service.validate_parameters(validation_data)
        elif validation_type == "pattern":
            result = await service.validate_pattern(validation_data)
        elif validation_type == "sequence":
            result = await service.validate_sequence(validation_data)
        elif validation_type == "hardware":
            result = await service.validate_hardware(validation_data)
        else:
            error = ErrorCode.VALIDATION_ERROR
            raise HTTPException(
                status_code=error.get_status_code(),
                detail=format_error(error, f"Unknown validation type: {validation_type}")
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
            
        return {
            "type": validation_type,
            "valid": result["valid"],
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
            "timestamp": datetime.now().isoformat()
        }
        
    except ValidationError as e:
        error = ErrorCode.VALIDATION_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e), e.context)
        )
    except Exception as e:
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))
        )


@router.get("/rules/{rule_type}", response_model=Dict[str, Any])
async def get_validation_rules(rule_type: str) -> Dict[str, Any]:
    """Get validation rules for type."""
    service = get_service()
    
    try:
        rules = await service.get_rules(rule_type)
        return {
            "type": rule_type,
            "rules": rules,
            "timestamp": datetime.now().isoformat()
        }
    except ValidationError as e:
        error = ErrorCode.VALIDATION_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e), e.context)
        )
    except Exception as e:
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))
        )


@router.get("/health")
async def health_check() -> JSONResponse:
    """Check API and service health status."""
    service = get_service()
    
    try:
        status = {
            "service": "ok" if service.is_running else "error",
            "timestamp": datetime.now().isoformat()
        }
        
        if not service.is_running:
            error = ErrorCode.SERVICE_UNAVAILABLE
            return JSONResponse(
                status_code=error.get_status_code(),
                content=format_error(error, "Service not running")
            )
            
        return JSONResponse(status)
        
    except Exception as e:
        error = ErrorCode.INTERNAL_ERROR
        return JSONResponse(
            status_code=error.get_status_code(),
            content=format_error(error, str(e))
        )
