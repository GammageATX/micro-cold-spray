"""Equipment control endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from ..models.equipment import (
    GasFlowRequest, GasValveRequest, VacuumPumpRequest,
    GateValveRequest, ShutterRequest, FeederRequest
)
from ..service import CommunicationService
from ...base import get_service
from ...base.exceptions import ServiceError, ValidationError

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("/status")
async def get_equipment_status(
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Get equipment status."""
    try:
        return await service.equipment.get_status()
    except (ServiceError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/gas/flow")
async def set_gas_flow(
    request: GasFlowRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Set gas flow setpoint."""
    try:
        await service.equipment.set_gas_flow(request.flow_type, request.value)
        return {"status": "ok"}
    except (ServiceError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/gas/valve")
async def set_gas_valve(
    request: GasValveRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Control gas valve."""
    try:
        await service.equipment.set_gas_valve(request.valve, request.state)
        return {"status": "ok"}
    except (ServiceError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/vacuum/pump")
async def control_vacuum_pump(
    request: VacuumPumpRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Control vacuum pump."""
    try:
        await service.equipment.control_vacuum_pump(request.pump, request.state)
        return {"status": "ok"}
    except (ServiceError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/vacuum/gate")
async def control_gate_valve(
    request: GateValveRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Control vacuum gate valve."""
    try:
        await service.equipment.control_gate_valve(request.position)
        return {"status": "ok"}
    except (ServiceError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/shutter")
async def control_shutter(
    request: ShutterRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Control nozzle shutter."""
    try:
        await service.equipment.control_shutter(request.state)
        return {"status": "ok"}
    except (ServiceError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/feeder")
async def control_feeder(
    request: FeederRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Control powder feeder."""
    try:
        if request.start:
            await service.feeder.start_feeder(request.frequency)
        else:
            await service.feeder.stop_feeder()
        return {"status": "ok"}
    except (ServiceError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
