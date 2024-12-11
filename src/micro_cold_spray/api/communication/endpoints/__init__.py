"""Hardware communication endpoint components."""

from .. import HardwareError
from .equipment import router as equipment_router
from .motion import router as motion_router
from .tags import router as tags_router

__all__ = [
    'equipment_router',
    'motion_router',
    'tags_router',
    'HardwareError'
]
