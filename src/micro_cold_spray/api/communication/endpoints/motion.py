"""Motion control endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Request, status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.communication.models.motion import (
    Position,
    SystemStatus,
    JogRequest,
    MoveRequest
)

router = APIRouter(prefix="/motion", tags=["motion"])


@router.get("/position", response_model=Position)
async def get_position(request: Request) -> Position:
    """Get current position.
    
    Returns:
        Current position
    """
    try:
        service = request.app.state.service
        if not service.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running"
            )

        position = await service.motion.get_position()
        return position

    except Exception as e:
        error_msg = "Failed to get position"
        logger.error(f"{error_msg}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"{error_msg}: {str(e)}"
        )


@router.get("/status", response_model=SystemStatus)
async def get_status(request: Request) -> SystemStatus:
    """Get motion system status.
    
    Returns:
        System status
    """
    try:
        service = request.app.state.service
        if not service.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running"
            )

        system_status = await service.motion.get_status()
        return system_status

    except Exception as e:
        error_msg = "Failed to get status"
        logger.error(f"{error_msg}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"{error_msg}: {str(e)}"
        )


@router.post("/jog/{axis}")
async def jog_axis(request: Request, axis: str, jog: JogRequest):
    """Perform relative move on single axis."""
    try:
        await request.app.state.service.motion.jog_axis(
            axis=axis.lower(),
            distance=jog.distance,
            velocity=jog.velocity
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to jog {axis} axis: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to jog {axis} axis: {str(e)}"
        )


@router.post("/move")
async def move(request: Request, move: MoveRequest):
    """Execute coordinated move."""
    try:
        await request.app.state.service.motion.move(
            x=move.x,
            y=move.y,
            z=move.z,
            velocity=move.velocity,
            wait_complete=move.wait_complete
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to execute move: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to execute move: {str(e)}"
        )


@router.post("/home/set")
async def set_home(request: Request):
    """Set current position as home."""
    try:
        await request.app.state.service.motion.set_home()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set home: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set home: {str(e)}"
        )


@router.post("/home/move")
async def move_to_home(request: Request):
    """Move to home position."""
    try:
        await request.app.state.service.motion.move_to_home()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to move to home: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to move to home: {str(e)}"
        )
