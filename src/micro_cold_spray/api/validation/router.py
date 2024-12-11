from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional

from .service import ValidationService, ValidationError

router = APIRouter(prefix="/validation", tags=["validation"])
_service: Optional[ValidationService] = None


def init_router(service: ValidationService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service


def get_service() -> ValidationService:
    """Get validation service instance."""
    if _service is None:
        raise RuntimeError("Validation service not initialized")
    return _service


@router.post("/validate")
async def validate_data(request: Dict[str, Any]) -> Dict[str, Any]:
    """Validate data against rules."""
    service = get_service()
    try:
        result = await service.validate(
            request["type"],
            request["data"]
        )
        return result
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )


@router.get("/rules/{rule_type}")
async def get_validation_rules(rule_type: str) -> Dict[str, Any]:
    """Get validation rules for type."""
    service = get_service()
    try:
        rules = await service.get_rules(rule_type)
        return {"rules": rules}
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e)}
        )


@router.get("/health")
async def health_check(
    service: ValidationService = Depends(get_service)
):
    """Check API health status."""
    try:
        # Check validation rules loaded
        status = await service.check_rules_loaded()
        if not status:
            return {
                "status": "Error",
                "error": "Validation rules not loaded"
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
