"""Motion control endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict

from .. import HardwareError
from ..router import get_plc_service
from ..services.plc_service import PLCTagService
from ..models.motion import (
    SingleAxisMoveRequest,
    CoordinatedMoveRequest,
    MotionStatus
)

router = APIRouter(prefix="/motion", tags=["motion"])


@router.post("/move")
async def move_axis(
    request: SingleAxisMoveRequest,
    plc_service: PLCTagService = Depends(get_plc_service)
) -> Dict[str, str]:
    """Execute single axis move."""
    try:
        # Write motion parameters
        await plc_service.write_tag(f"motion.{request.axis}.target", request.position)
        await plc_service.write_tag(f"motion.{request.axis}.velocity", request.velocity)
        
        # Trigger move
        await plc_service.write_tag(f"motion.{request.axis}.start", True)
        return {"status": "started"}
    except HardwareError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "device": e.device, "context": e.context}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/move/xy")
async def move_xy(
    request: CoordinatedMoveRequest,
    plc_service: PLCTagService = Depends(get_plc_service)
) -> Dict[str, str]:
    """Execute coordinated XY move."""
    try:
        # Write motion parameters
        await plc_service.write_tag("motion.x.target", request.x_position)
        await plc_service.write_tag("motion.y.target", request.y_position)
        await plc_service.write_tag("motion.xy.velocity", request.velocity)
        
        # Trigger coordinated move
        await plc_service.write_tag("motion.xy.start", True)
        return {"status": "started"}
    except HardwareError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "device": e.device, "context": e.context}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_motion_status(
    plc_service: PLCTagService = Depends(get_plc_service)
) -> MotionStatus:
    """Get current motion status."""
    try:
        # Read axis positions
        x_pos = await plc_service.read_tag("motion.x.position")
        y_pos = await plc_service.read_tag("motion.y.position")
        z_pos = await plc_service.read_tag("motion.z.position")
        
        # Read axis states
        x_moving = await plc_service.read_tag("motion.x.moving")
        y_moving = await plc_service.read_tag("motion.y.moving")
        z_moving = await plc_service.read_tag("motion.z.moving")
        
        # Read error states
        x_error = await plc_service.read_tag("motion.x.error")
        y_error = await plc_service.read_tag("motion.y.error")
        z_error = await plc_service.read_tag("motion.z.error")
        
        return MotionStatus(
            x_position=x_pos,
            y_position=y_pos,
            z_position=z_pos,
            x_moving=x_moving,
            y_moving=y_moving,
            z_moving=z_moving,
            x_error=x_error,
            y_error=y_error,
            z_error=z_error
        )
    except HardwareError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "device": e.device, "context": e.context}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
