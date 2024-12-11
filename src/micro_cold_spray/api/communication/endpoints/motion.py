"""Motion control endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends

from ..exceptions import HardwareError
from ..services import MotionService
from ..models.motion import (
    SingleAxisMoveRequest,
    CoordinatedMoveRequest,
    MotionStatus
)

router = APIRouter(prefix="/motion", tags=["motion"])

# Service instance
_motion_service: MotionService | None = None


def init_router(motion: MotionService) -> None:
    """Initialize router with service instance."""
    global _motion_service
    _motion_service = motion


def get_motion_service() -> MotionService:
    """Get motion service instance."""
    if not _motion_service:
        raise RuntimeError("Motion service not initialized")
    return _motion_service


@router.post("/move")
async def move_axis(
    request: SingleAxisMoveRequest,
    motion: MotionService = Depends(get_motion_service)
) -> Dict[str, Any]:
    """Execute single axis move."""
    try:
        await motion.move_axis(
            request.axis,
            request.position,
            request.velocity
        )
        return {"status": "ok"}
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except HardwareError as e:
        return {
            "status": "error",
            "message": str(e),
            "device": e.device,
            "context": e.context
        }


@router.post("/move/xy")
async def move_xy(
    request: CoordinatedMoveRequest,
    motion: MotionService = Depends(get_motion_service)
) -> Dict[str, Any]:
    """Execute coordinated XY move."""
    try:
        await motion.move_xy(
            request.x_position,
            request.y_position,
            request.velocity
        )
        return {"status": "ok"}
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except HardwareError as e:
        return {
            "status": "error",
            "message": str(e),
            "device": e.device,
            "context": e.context
        }


@router.get("/status")
async def get_motion_status(
    motion: MotionService = Depends(get_motion_service)
) -> MotionStatus:
    """Get current motion status."""
    return await motion.get_status()
