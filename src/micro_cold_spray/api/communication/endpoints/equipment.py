from fastapi import APIRouter, HTTPException, Depends

from ..services.plc_service import PLCTagService
from ..services.tag_cache import TagCacheService
from ..models.equipment import (
    GasFlowRequest, GasValveRequest, PumpRequest,
    VacuumValveRequest, FeederRequest, DeagglomeratorRequest,
    NozzleRequest, ShutterRequest
)

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.post("/gas/flow")
async def set_gas_flow(
    request: GasFlowRequest,
    plc_service: PLCTagService = Depends(get_plc_service)
):
    """Set gas flow setpoint."""
    try:
        tag_path = f"gas_control.{request.type}_flow.setpoint"
        await plc_service.write_tag(tag_path, request.value)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/gas/valve")
async def control_gas_valve(
    request: GasValveRequest,
    plc_service: PLCTagService = Depends(get_plc_service)
):
    """Control gas valve."""
    try:
        tag_path = f"valve_control.{request.valve}_gas"
        await plc_service.write_tag(tag_path, request.state)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pump")
async def control_pump(
    request: PumpRequest,
    plc_service: PLCTagService = Depends(get_plc_service)
):
    """Control vacuum pump."""
    try:
        tag_path = "pump_control.enable"
        await plc_service.write_tag(tag_path, request.state)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/vacuum/valve")
async def control_vacuum_valve(
    request: VacuumValveRequest,
    plc_service: PLCTagService = Depends(get_plc_service)
):
    """Control vacuum valve."""
    try:
        tag_path = f"valve_control.{request.valve}_vacuum"
        await plc_service.write_tag(tag_path, request.state)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/feeder")
async def control_feeder(
    request: FeederRequest,
    plc_service: PLCTagService = Depends(get_plc_service)
):
    """Control powder feeder."""
    try:
        tag_path = "feeder_control.enable"
        await plc_service.write_tag(tag_path, request.state)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/deagglomerator")
async def control_deagglomerator(
    request: DeagglomeratorRequest,
    plc_service: PLCTagService = Depends(get_plc_service)
):
    """Control deagglomerator."""
    try:
        tag_path = "deagglomerator_control.enable"
        await plc_service.write_tag(tag_path, request.state)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/nozzle")
async def control_nozzle(
    request: NozzleRequest,
    plc_service: PLCTagService = Depends(get_plc_service)
):
    """Control nozzle heater."""
    try:
        tag_path = "nozzle_control.enable"
        await plc_service.write_tag(tag_path, request.state)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/shutter")
async def control_shutter(
    request: ShutterRequest,
    plc_service: PLCTagService = Depends(get_plc_service)
):
    """Control nozzle shutter."""
    try:
        tag_path = "shutter_control.position"
        await plc_service.write_tag(tag_path, request.position)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
