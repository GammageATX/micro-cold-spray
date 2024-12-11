"""FastAPI router for hardware communication."""

from typing import Dict, Any
from fastapi import APIRouter, Depends

from .exceptions import HardwareError
from .endpoints import tags, motion, equipment
from .services import (
    EquipmentService,
    FeederService,
    MotionService,
    TagCacheService,
    TagMappingService
)

router = APIRouter(prefix="/communication", tags=["communication"])

# Initialize sub-routers
router.include_router(equipment.router)
router.include_router(motion.router)
router.include_router(tags.router)

# Service instances
_equipment_service: EquipmentService | None = None
_feeder_service: FeederService | None = None
_motion_service: MotionService | None = None
_tag_cache: TagCacheService | None = None
_tag_mapping: TagMappingService | None = None


def init_router(
    equipment: EquipmentService,
    feeder: FeederService,
    motion: MotionService,
    tag_cache: TagCacheService,
    tag_mapping: TagMappingService
) -> None:
    """Initialize router with service instances."""
    global _equipment_service, _feeder_service, _motion_service, _tag_cache, _tag_mapping
    
    # Store service instances
    _equipment_service = equipment
    _feeder_service = feeder
    _motion_service = motion
    _tag_cache = tag_cache
    _tag_mapping = tag_mapping
    
    # Initialize sub-routers
    equipment.init_router(_equipment_service, _feeder_service)
    motion.init_router(_motion_service)
    tags.init_router(_tag_cache, _tag_mapping)


def get_equipment_service() -> EquipmentService:
    """Get equipment service instance."""
    if not _equipment_service:
        raise RuntimeError("Equipment service not initialized")
    return _equipment_service


def get_feeder_service() -> FeederService:
    """Get feeder service instance."""
    if not _feeder_service:
        raise RuntimeError("Feeder service not initialized")
    return _feeder_service


def get_motion_service() -> MotionService:
    """Get motion service instance."""
    if not _motion_service:
        raise RuntimeError("Motion service not initialized")
    return _motion_service


def get_tag_cache() -> TagCacheService:
    """Get tag cache instance."""
    if not _tag_cache:
        raise RuntimeError("Tag cache not initialized")
    return _tag_cache


def get_tag_mapping() -> TagMappingService:
    """Get tag mapping instance."""
    if not _tag_mapping:
        raise RuntimeError("Tag mapping not initialized")
    return _tag_mapping


@router.get("/health")
async def health_check(
    equipment: EquipmentService = Depends(get_equipment_service),
    feeder: FeederService = Depends(get_feeder_service),
    motion: MotionService = Depends(get_motion_service),
    tag_cache: TagCacheService = Depends(get_tag_cache),
    tag_mapping: TagMappingService = Depends(get_tag_mapping)
) -> Dict[str, Any]:
    """Check API health status.
    
    Returns:
        Dict containing health status and any error details
    """
    try:
        status = {
            "equipment": equipment.is_running,
            "feeder": feeder.is_running,
            "motion": motion.is_running,
            "tag_cache": tag_cache.is_running,
            "tag_mapping": tag_mapping.is_running
        }
        
        return {
            "status": "healthy" if all(status.values()) else "degraded",
            "components": status
        }
        
    except HardwareError as e:
        return {
            "status": "error",
            "message": str(e),
            "device": e.device,
            "context": e.context
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
