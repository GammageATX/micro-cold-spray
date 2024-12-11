"""FastAPI router for validation endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional

from .service import ValidationService, ValidationError

router = APIRouter(prefix="/validation", tags=["validation"])
_service: Optional[ValidationService] = None


def init_router(service: ValidationService) -> None:
    """Initialize router with service instance.
    
    Args:
        service: Validation service instance
    """
    global _service
    _service = service


def get_service() -> ValidationService:
    """Get validation service instance.
    
    Returns:
        ValidationService instance
        
    Raises:
        RuntimeError: If service not initialized
    """
    if _service is None:
        raise RuntimeError("Validation service not initialized")
    return _service


@router.post("/validate")
async def validate_data(request: Dict[str, Any]) -> Dict[str, Any]:
    """Validate data against rules.
    
    Args:
        request: Dictionary containing:
            - type: Type of validation to perform
            - data: Data to validate
            
    Returns:
        Dictionary containing validation results
        
    Raises:
        HTTPException: If validation fails
    """
    service = get_service()
    try:
        # Validate request format
        if "type" not in request:
            raise ValidationError("Missing validation type")
        if "data" not in request:
            raise ValidationError("Missing validation data")
            
        # Perform validation
        result = await service._handle_validation_request(request)
        return result
        
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Validation failed: {str(e)}"}
        )


@router.get("/rules/{rule_type}")
async def get_validation_rules(rule_type: str) -> Dict[str, Any]:
    """Get validation rules for type.
    
    Args:
        rule_type: Type of rules to retrieve
        
    Returns:
        Dictionary containing rules
        
    Raises:
        HTTPException: If rules not found
    """
    service = get_service()
    try:
        rules = await service.get_rules(rule_type)
        return {"rules": rules}
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to get rules: {str(e)}"}
        )


@router.get("/health")
async def health_check(
    service: ValidationService = Depends(get_service)
) -> Dict[str, Any]:
    """Check API health status.
    
    Returns:
        Dictionary containing:
            - status: Service status
            - error: Error message if any
    """
    try:
        if not service.is_running:
            return {
                "status": "Error",
                "error": "Service not running"
            }
            
        return {
            "status": "Running",
            "error": None
        }
    except Exception as e:
        return {
            "status": "Error",
            "error": str(e)
        }
