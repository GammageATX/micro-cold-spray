"""Equipment router."""

from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from ..service import CommunicationService
from ..dependencies import get_service
from ...base.exceptions import ServiceError, ValidationError


class EquipmentResponse(BaseModel):
    """Equipment response model."""
    status: str
    message: str
    timestamp: datetime


class EquipmentStatusResponse(BaseModel):
    """Equipment status response model."""
    status: str
    equipment_id: str
    state: Dict[str, Any]
    timestamp: datetime


class EquipmentListResponse(BaseModel):
    """Equipment list response model."""
    status: str
    equipment: List[Dict[str, Any]]
    timestamp: datetime


class GasFlowRequest(BaseModel):
    """Gas flow request model."""
    flow_type: str = Field(..., description="Type of gas flow to set")
    value: float = Field(..., description="Flow value to set")


router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get(
    "/status/{equipment_id}",
    response_model=EquipmentStatusResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Equipment not found"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def get_equipment_status(
    equipment_id: str,
    service: CommunicationService = Depends(get_service)
):
    """Get equipment status."""
    try:
        # Get equipment status
        status_data = await service.equipment_service.get_status(equipment_id)
        
        return EquipmentStatusResponse(
            status="ok",
            equipment_id=equipment_id,
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
    response_model=EquipmentListResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def list_equipment(service: CommunicationService = Depends(get_service)):
    """List available equipment."""
    try:
        # Get equipment list
        equipment_list = await service.equipment_service.list_equipment()
        
        return EquipmentListResponse(
            status="ok",
            equipment=equipment_list,
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
    "/gas/flow",
    response_model=EquipmentResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def set_gas_flow(
    request: GasFlowRequest,
    service: CommunicationService = Depends(get_service)
):
    """Set gas flow."""
    try:
        # Set gas flow
        await service.equipment_service.set_gas_flow(
            flow_type=request.flow_type,
            value=request.value
        )
        
        return EquipmentResponse(
            status="ok",
            message=f"Gas flow {request.flow_type} set to {request.value}",
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
    "/valve/{valve_id}/state",
    response_model=EquipmentResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request"},
        status.HTTP_404_NOT_FOUND: {"description": "Valve not found"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def set_valve_state(
    valve_id: str,
    state: bool,
    service: CommunicationService = Depends(get_service)
):
    """Set valve state."""
    try:
        # Set valve state
        await service.equipment_service.set_valve_state(valve_id, state)
        
        return EquipmentResponse(
            status="ok",
            message=f"Valve {valve_id} {'opened' if state else 'closed'}",
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
