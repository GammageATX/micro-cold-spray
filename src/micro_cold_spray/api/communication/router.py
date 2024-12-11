from fastapi import APIRouter, Depends
from .endpoints import tags, motion, equipment
from .services.plc_service import PLCTagService
from .services.tag_cache import TagCacheService
from typing import Optional

router = APIRouter(prefix="/communication")
router.include_router(tags.router)
router.include_router(motion.router)
router.include_router(equipment.router)

_plc_service: Optional[PLCTagService] = None
_tag_cache: Optional[TagCacheService] = None


def init_router(plc_service: PLCTagService, tag_cache: TagCacheService) -> None:
    """Initialize router with service instances."""
    global _plc_service, _tag_cache
    _plc_service = plc_service
    _tag_cache = tag_cache


def get_plc_service() -> PLCTagService:
    """Get PLC service instance."""
    if _plc_service is None:
        raise RuntimeError("PLC service not initialized")
    return _plc_service


def get_tag_cache() -> TagCacheService:
    """Get tag cache instance."""
    if _tag_cache is None:
        raise RuntimeError("Tag cache not initialized")
    return _tag_cache


@router.get("/health")
async def health_check(
    plc_service: PLCTagService = Depends(get_plc_service),
    tag_cache: TagCacheService = Depends(get_tag_cache)
):
    """Check API health status."""
    try:
        # Check PLC connection
        plc_status = await plc_service.check_connection()
        
        if not plc_status:
            return {
                "status": "Error",
                "error": "PLC connection failed"
            }
            
        # Check tag cache
        cache_status = await tag_cache.check_status()
        
        if not cache_status:
            return {
                "status": "Error",
                "error": "Tag cache error"
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
