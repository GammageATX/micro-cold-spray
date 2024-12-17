"""FastAPI router for validation endpoints."""

from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse
from loguru import logger

from .service import ValidationService
from .exceptions import ValidationError
from ..base.router import add_health_endpoints
from ..base.errors import ErrorCode, format_error

# Create FastAPI app
app = FastAPI(title="Validation API")

router = APIRouter(prefix="/validation", tags=["validation"])
_service: Optional[ValidationService] = None


def init_router(service: ValidationService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service
    add_health_endpoints(app, service)


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

# Add router to app
app.include_router(router)
