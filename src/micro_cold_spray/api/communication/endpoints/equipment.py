"""Equipment control endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends

from ..exceptions import HardwareError
from ..services import EquipmentService, FeederService
from ..models.equipment import (
    GasFlowRequest,
    GasValveRequest,
    PumpRequest,
    VacuumValveRequest,
    NozzleRequest,
    ShutterRequest,
    FeederRequest
)

router = APIRouter(prefix="/equipment", tags=["equipment"])

# Service instances
_equipment_service: EquipmentService | None = None
_feeder_service: FeederService | None = None


def init_router(equipment: EquipmentService, feeder: FeederService) -> None:
    """Initialize router with service instances."""
    global _equipment_service, _feeder_service
    _equipment_service = equipment
    _feeder_service = feeder


def get_equipment_service() -> EquipmentService:
    """Get equipment service instance."""
    if not _equipment_service:
        raise RuntimeError("Equipment service not initialized")
    return _equipment_service


def get_feeder_service() -> FeederService:
    """Get feeder service instance."""
    if not _feeder_service:
        raise RuntimeError("Feeder service not initialized")
    return _feeder_service


@router.get("/status")
async def get_equipment_status(
    equipment: EquipmentService = Depends(get_equipment_service),
    feeder: FeederService = Depends(get_feeder_service)
) -> Dict[str, Any]:
    """Get equipment status.
    
    Returns:
        Dictionary with equipment status
    """
    try:
        equipment_status = await equipment.get_status()
        feeder_status = await feeder.get_status()
        
        return {
            **equipment_status,
            "feeder": feeder_status
        }
        
    except HardwareError as e:
        return {
            "status": "error",
            "message": str(e),
            "device": e.device,
            "context": e.context
        }


@router.post("/gas/flow")
async def set_gas_flow(
    request: GasFlowRequest,
    equipment: EquipmentService = Depends(get_equipment_service)
) -> Dict[str, Any]:
    """Set gas flow setpoint."""
    await equipment.set_gas_flow(request)
    return {"status": "ok"}


@router.post("/gas/valve")
async def set_gas_valve(
    request: GasValveRequest,
    equipment: EquipmentService = Depends(get_equipment_service)
) -> Dict[str, Any]:
    """Control gas valve."""
    await equipment.set_gas_valve(request)
    return {"status": "ok"}


@router.post("/vacuum/pump")
async def control_pump(
    request: PumpRequest,
    equipment: EquipmentService = Depends(get_equipment_service)
) -> Dict[str, Any]:
    """Control vacuum pump."""
    await equipment.control_pump(request)
    return {"status": "ok"}


@router.post("/vacuum/valve")
async def set_vacuum_valve(
    request: VacuumValveRequest,
    equipment: EquipmentService = Depends(get_equipment_service)
) -> Dict[str, Any]:
    """Control vacuum valve."""
    await equipment.set_vacuum_valve(request)
    return {"status": "ok"}


@router.post("/nozzle/heater")
async def control_nozzle(
    request: NozzleRequest,
    equipment: EquipmentService = Depends(get_equipment_service)
) -> Dict[str, Any]:
    """Control nozzle heater."""
    await equipment.control_nozzle(request)
    return {"status": "ok"}


@router.post("/nozzle/shutter")
async def control_shutter(
    request: ShutterRequest,
    equipment: EquipmentService = Depends(get_equipment_service)
) -> Dict[str, Any]:
    """Control nozzle shutter."""
    await equipment.control_shutter(request)
    return {"status": "ok"}


@router.post("/feeder")
async def control_feeder(
    request: FeederRequest,
    feeder: FeederService = Depends(get_feeder_service)
) -> Dict[str, Any]:
    """Control powder feeder."""
    if request.start:
        await feeder.start_feeder()
    else:
        await feeder.stop_feeder()
        
    if request.speed is not None:
        await feeder.set_speed(request.speed)
        
    return {"status": "ok"}
