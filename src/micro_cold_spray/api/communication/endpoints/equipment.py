"""Equipment control endpoints."""

from typing import Dict, Any, Literal
from fastapi import APIRouter, Request, status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.communication.models.equipment import (
    EquipmentState,
    GasFlowRequest,
    GasValveRequest,
    VacuumPumpRequest,
    GateValveRequest,
    ShutterRequest,
    FeederRequest,
    DeagglomeratorRequest
)

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("/state", response_model=EquipmentState)
async def get_state(request: Request) -> EquipmentState:
    """Get current equipment state.
    
    Returns:
        Current equipment state
    """
    try:
        service = request.app.state.service
        if not service.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running"
            )

        state = await service.equipment.get_state()
        return state

    except Exception as e:
        error_msg = "Failed to get equipment state"
        logger.error(f"{error_msg}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"{error_msg}: {str(e)}"
        )


@router.post("/gas/main/flow")
async def set_main_flow(request: Request, flow: GasFlowRequest):
    """Set main gas flow rate."""
    try:
        await request.app.state.service.equipment.set_main_flow(flow.flow_rate)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set main flow: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set main flow: {str(e)}"
        )


@router.post("/gas/feeder/flow")
async def set_feeder_flow(request: Request, flow: GasFlowRequest):
    """Set feeder gas flow rate."""
    try:
        await request.app.state.service.equipment.set_feeder_flow(flow.flow_rate)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set feeder flow: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set feeder flow: {str(e)}"
        )


@router.post("/feeder/{feeder_id}/frequency")
async def set_feeder_frequency(
    request: Request,
    feeder_id: int,
    freq: FeederRequest
):
    """Set feeder frequency."""
    try:
        await request.app.state.equipment.set_feeder_frequency(feeder_id, freq.frequency)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set feeder {feeder_id} frequency: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set feeder {feeder_id} frequency: {str(e)}"
        )


@router.post("/feeder/{feeder_id}/start")
async def start_feeder(request: Request, feeder_id: int):
    """Start feeder."""
    try:
        await request.app.state.equipment.start_feeder(feeder_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to start feeder {feeder_id}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to start feeder {feeder_id}: {str(e)}"
        )


@router.post("/feeder/{feeder_id}/stop")
async def stop_feeder(request: Request, feeder_id: int):
    """Stop feeder."""
    try:
        await request.app.state.equipment.stop_feeder(feeder_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to stop feeder {feeder_id}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to stop feeder {feeder_id}: {str(e)}"
        )


@router.post("/deagg/{deagg_id}/speed")
async def set_deagg_speed(
    request: Request,
    deagg_id: int,
    speed: DeagglomeratorRequest
):
    """Set deagglomerator speed."""
    try:
        await request.app.state.equipment.set_deagg_speed(deagg_id, speed.speed)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set deagg {deagg_id} speed: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set deagg {deagg_id} speed: {str(e)}"
        )


@router.post("/nozzle/select")
async def select_nozzle(request: Request, nozzle_id: Literal[1, 2]):
    """Select active nozzle."""
    try:
        await request.app.state.service.equipment.select_nozzle(nozzle_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to select nozzle: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to select nozzle: {str(e)}"
        )


@router.post("/nozzle/shutter/open")
async def open_shutter(request: Request):
    """Open shutter."""
    try:
        await request.app.state.service.equipment.set_shutter(True)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to open shutter: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to open shutter: {str(e)}"
        )


@router.post("/nozzle/shutter/close")
async def close_shutter(request: Request):
    """Close shutter."""
    try:
        await request.app.state.service.equipment.set_shutter(False)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to close shutter: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to close shutter: {str(e)}"
        )


@router.post("/gas/main/valve")
async def set_main_gas_valve(request: Request, valve: GasValveRequest):
    """Control main gas valve."""
    try:
        await request.app.state.service.equipment.set_main_gas_valve(valve.open)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to control main gas valve: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to control main gas valve: {str(e)}"
        )


@router.post("/gas/feeder/valve")
async def set_feeder_gas_valve(request: Request, valve: GasValveRequest):
    """Control feeder gas valve."""
    try:
        await request.app.state.service.equipment.set_feeder_gas_valve(valve.open)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to control feeder gas valve: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to control feeder gas valve: {str(e)}"
        )


@router.post("/vacuum/gate")
async def set_gate_valve(request: Request, valve: GateValveRequest):
    """Control gate valve position."""
    try:
        await request.app.state.service.equipment.set_gate_valve_position(valve.position)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to control gate valve: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to control gate valve: {str(e)}"
        )


@router.post("/vacuum/vent/open")
async def open_vent_valve(request: Request):
    """Open vent valve."""
    try:
        await request.app.state.service.equipment.set_vent_valve(True)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to open vent valve: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to open vent valve: {str(e)}"
        )


@router.post("/vacuum/vent/close")
async def close_vent_valve(request: Request):
    """Close vent valve."""
    try:
        await request.app.state.service.equipment.set_vent_valve(False)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to close vent valve: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to close vent valve: {str(e)}"
        )


@router.post("/vacuum/mech/start")
async def start_mech_pump(request: Request):
    """Start mechanical pump."""
    try:
        await request.app.state.service.equipment.start_mech_pump()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to start mechanical pump: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to start mechanical pump: {str(e)}"
        )


@router.post("/vacuum/mech/stop")
async def stop_mech_pump(request: Request):
    """Stop mechanical pump."""
    try:
        await request.app.state.service.equipment.stop_mech_pump()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to stop mechanical pump: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to stop mechanical pump: {str(e)}"
        )


@router.post("/vacuum/booster/start")
async def start_booster_pump(request: Request):
    """Start booster pump."""
    try:
        await request.app.state.service.equipment.start_booster_pump()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to start booster pump: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to start booster pump: {str(e)}"
        )


@router.post("/vacuum/booster/stop")
async def stop_booster_pump(request: Request):
    """Stop booster pump."""
    try:
        await request.app.state.service.equipment.stop_booster_pump()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to stop booster pump: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to stop booster pump: {str(e)}"
        )


@router.post("/deagg/{deagg_id}/set")
async def set_deagglomerator(
    request: Request,
    deagg_id: Literal[1, 2],
    params: DeagglomeratorRequest
):
    """Set deagglomerator parameters."""
    try:
        await request.app.state.service.equipment.set_deagglomerator(
            deagg_id=deagg_id,
            duty_cycle=params.duty_cycle,
            frequency=params.frequency
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set deagglomerator {deagg_id}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set deagglomerator {deagg_id}: {str(e)}"
        )
