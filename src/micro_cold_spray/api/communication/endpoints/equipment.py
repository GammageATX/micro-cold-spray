"""Equipment control endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends

from ..models.equipment import (
    GasFlowRequest, GasValveRequest, PumpRequest,
    VacuumValveRequest, NozzleRequest, ShutterRequest, FeederRequest
)
from ..service import CommunicationService
from ...base import get_service

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("/status")
async def get_equipment_status(
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Get equipment status."""
    try:
        return await service.equipment.get_status()
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/gas/flow")
async def set_gas_flow(
    request: GasFlowRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Set gas flow setpoint."""
    await service.equipment.set_gas_flow(request)
    return {"status": "ok"}


@router.post("/gas/valve")
async def set_gas_valve(
    request: GasValveRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Control gas valve."""
    await service.equipment.set_gas_valve(request)
    return {"status": "ok"}


@router.post("/vacuum/pump")
async def control_pump(
    request: PumpRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Control vacuum pump."""
    await service.equipment.control_pump(request)
    return {"status": "ok"}


@router.post("/vacuum/valve")
async def set_vacuum_valve(
    request: VacuumValveRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Control vacuum valve."""
    await service.equipment.set_vacuum_valve(request)
    return {"status": "ok"}


@router.post("/nozzle/heater")
async def control_nozzle(
    request: NozzleRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Control nozzle heater."""
    await service.equipment.control_nozzle(request)
    return {"status": "ok"}


@router.post("/nozzle/shutter")
async def control_shutter(
    request: ShutterRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Control nozzle shutter."""
    await service.equipment.control_shutter(request)
    return {"status": "ok"}


@router.post("/feeder")
async def control_feeder(
    request: FeederRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Control powder feeder."""
    if request.start:
        await service.feeder.start_feeder()
    else:
        await service.feeder.stop_feeder()
        
    if request.speed is not None:
        await service.feeder.set_speed(request.speed)
        
    return {"status": "ok"}
