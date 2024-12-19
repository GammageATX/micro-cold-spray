"""Motion router."""

from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from ..service import CommunicationService
from ..dependencies import get_service
from ...base.exceptions import ServiceError, ValidationError


class MotionResponse(BaseModel):
    """Motion response model."""
    status: str
    message: str
    timestamp: datetime


class MotionStatusResponse(BaseModel):
    """Motion status response model."""
    status: str
    axis_id: str
    state: Dict[str, Any]
    timestamp: datetime


class MotionListResponse(BaseModel):
    """Motion list response model."""
    status: str
    axes: List[Dict[str, Any]]
    timestamp: datetime


class MoveRequest(BaseModel):
    """Move request model."""
    axis_id: str = Field(..., description="Axis to move")
    position: float = Field(..., description="Target position")
    velocity: float = Field(None, description="Optional velocity override")


router = APIRouter(prefix="/motion", tags=["motion"])


@router.get(
    "/status/{axis_id}",
    response_model=MotionStatusResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Axis not found"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def get_axis_status(
    axis_id: str,
    service: CommunicationService = Depends(get_service)
):
    """Get axis status."""
    try:
        # Get axis status
        status_data = await service.motion_service.get_status(axis_id)
        
        return MotionStatusResponse(
            status="ok",
            axis_id=axis_id,
            state=status_data,
            timestamp=datetime.now()
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/list",
    response_model=MotionListResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def list_axes(service: CommunicationService = Depends(get_service)):
    """List available axes."""
    try:
        # Get axes list
        axes_list = await service.motion_service.list_axes()
        
        return MotionListResponse(
            status="ok",
            axes=axes_list,
            timestamp=datetime.now()
        )
        
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/move",
    response_model=MotionResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request"},
        status.HTTP_404_NOT_FOUND: {"description": "Axis not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def move_axis(
    request: MoveRequest,
    service: CommunicationService = Depends(get_service)
):
    """Move axis to position."""
    try:
        # Move axis
        await service.motion_service.move_axis(
            axis_id=request.axis_id,
            position=request.position,
            velocity=request.velocity
        )
        
        return MotionResponse(
            status="ok",
            message=f"Moving axis {request.axis_id} to position {request.position}",
            timestamp=datetime.now()
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/stop/{axis_id}",
    response_model=MotionResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Axis not found"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def stop_axis(
    axis_id: str,
    service: CommunicationService = Depends(get_service)
):
    """Stop axis motion."""
    try:
        # Stop axis
        await service.motion_service.stop_axis(axis_id)
        
        return MotionResponse(
            status="ok",
            message=f"Stopped axis {axis_id}",
            timestamp=datetime.now()
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
