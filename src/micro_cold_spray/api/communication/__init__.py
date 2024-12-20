"""Communication module for hardware control."""

from .communication_service import CommunicationService
from .communication_router import router
from .models.equipment import EquipmentState
from .models.motion import Position, Velocity
from .models.tags import TagValue, TagMetadata, TagCacheResponse
from .services.equipment import EquipmentService
from .services.feeder import FeederService
from .services.motion import MotionService
from .services.tag_cache import TagCacheService
from .services.tag_mapping import TagMappingService

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
