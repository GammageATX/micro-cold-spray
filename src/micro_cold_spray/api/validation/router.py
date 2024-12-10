from fastapi import APIRouter, HTTPException
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