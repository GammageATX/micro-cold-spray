"""Communication API package."""

from micro_cold_spray.api.communication.communication_service import CommunicationService
from micro_cold_spray.api.communication.endpoints import equipment_router, motion_router, tags_router
from micro_cold_spray.api.communication.services import (
    EquipmentService,
    FeederService,
    MotionService,
    TagCacheService,
    TagMappingService
)
from micro_cold_spray.api.communication.dependencies import (
    get_communication_service,
    get_equipment_service,
    get_motion_service,
    get_tag_service,
    initialize_service,
    cleanup_service
)

__all__ = [
    # Core service
    "CommunicationService",
    
    # Routers
    "equipment_router",
    "motion_router",
    "tags_router",
    
    # Service classes
    "EquipmentService",
    "FeederService",
    "MotionService",
    "TagCacheService",
    "TagMappingService",
    
    # Dependencies
    "get_communication_service",
    "get_equipment_service",
    "get_motion_service",
    "get_tag_service",
    "initialize_service",
    "cleanup_service"
]
