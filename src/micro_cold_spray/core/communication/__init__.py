"""Communication module for hardware control.

Provides:
- Hardware communication clients (PLC, SSH)
- Equipment control services
- Motion control
- Tag management
- Real-time monitoring
"""

from micro_cold_spray.core.communication.services.service import CommunicationService
from micro_cold_spray.core.communication.router import router, app
from micro_cold_spray.core.communication.models.equipment import (
    GasFlowRequest, GasValveRequest, VacuumPumpRequest,
    GateValveRequest, ShutterRequest, FeederRequest
)
from .models.motion import (
    SingleAxisMoveRequest, CoordinatedMoveRequest,
    AxisStatus, MotionStatus
)
from .models.tags import (
    TagMetadata, TagValue, TagRequest, TagResponse,
    TagUpdate, TagSubscription, TagCacheResponse
)

__all__ = [
    # Service
    'CommunicationService',
    
    # Router
    'router',
    'app',
    
    # Equipment Models
    'GasFlowRequest',
    'GasValveRequest',
    'VacuumPumpRequest',
    'GateValveRequest',
    'ShutterRequest',
    'FeederRequest',
    
    # Motion Models
    'SingleAxisMoveRequest',
    'CoordinatedMoveRequest',
    'AxisStatus',
    'MotionStatus',
    
    # Tag Models
    'TagMetadata',
    'TagValue',
    'TagRequest',
    'TagResponse',
    'TagUpdate',
    'TagSubscription',
    'TagCacheResponse'
]
