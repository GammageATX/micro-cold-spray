"""Process API endpoints."""

from fastapi import APIRouter

from micro_cold_spray.api.process.endpoints.process_endpoints import router as process_router
from micro_cold_spray.api.process.endpoints.pattern_endpoints import router as pattern_router
from micro_cold_spray.api.process.endpoints.parameter_endpoints import router as parameter_router
from micro_cold_spray.api.process.endpoints.sequence_endpoints import router as sequence_router

# Create main router
router = APIRouter()

# Mount sub-routers
router.include_router(process_router)
router.include_router(pattern_router)
router.include_router(parameter_router)
router.include_router(sequence_router)

__all__ = ["router"]
