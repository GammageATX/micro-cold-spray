"""Communication endpoints."""

from micro_cold_spray.api.communication.endpoints.equipment import router as equipment_router
from micro_cold_spray.api.communication.endpoints.motion import router as motion_router
from micro_cold_spray.api.communication.endpoints.tags import router as tags_router

__all__ = [
    "equipment_router",
    "motion_router",
    "tags_router"
]
