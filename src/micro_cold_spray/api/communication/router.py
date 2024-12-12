"""FastAPI router for hardware communication."""

from typing import Dict, Any
from fastapi import APIRouter, Depends

from ..base import get_service
from .service import CommunicationService
from .endpoints import tags, motion, equipment

router = APIRouter(prefix="/communication", tags=["communication"])

# Initialize sub-routers
router.include_router(equipment.router)
router.include_router(motion.router)
router.include_router(tags.router)


def init_router() -> None:
    """Initialize router."""
    pass


@router.get("/health")
async def health_check(
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Check API health status."""
    try:
        status = await service.check_health()
        return status
    except Exception as e:
        return {"status": "error", "message": str(e)}
