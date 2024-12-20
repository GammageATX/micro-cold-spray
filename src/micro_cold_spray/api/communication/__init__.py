"""Communication module for hardware control."""

from micro_cold_spray.api.communication.communication_service import CommunicationService
from micro_cold_spray.api.communication.communication_router import router
from micro_cold_spray.api.communication.models.equipment import EquipmentState
from micro_cold_spray.api.communication.models.motion import Position, Velocity
from micro_cold_spray.api.communication.models.tags import TagValue, TagMetadata, TagCacheResponse
from micro_cold_spray.api.communication.services.equipment import EquipmentService
from micro_cold_spray.api.communication.services.feeder import FeederService
from micro_cold_spray.api.communication.services.motion import MotionService
from micro_cold_spray.api.communication.services.tag_cache import TagCacheService
from micro_cold_spray.api.communication.services.tag_mapping import TagMappingService

__all__ = [
    # Core components
    'CommunicationService',
    'router',
    # Models
    'EquipmentState',
    'Position',
    'Velocity',
    'TagValue',
    'TagMetadata',
    'TagCacheResponse',
    # Services
    'EquipmentService',
    'FeederService',
    'MotionService',
    'TagCacheService',
    'TagMappingService'
]
