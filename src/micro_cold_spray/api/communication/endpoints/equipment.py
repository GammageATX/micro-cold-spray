"""Equipment control endpoints."""

from typing import Dict, Any, Literal
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, status
from loguru import logger
import asyncio

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


# State query endpoint
@router.get("/state", response_model=EquipmentState)
async def get_state(request: Request) -> EquipmentState:
    """Get current equipment state."""
    try:
        service = request.app.state.service
        if not service.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running"
            )

        state = await service.get_state()
        return state

    except Exception as e:
        error_msg = "Failed to get equipment state"
        logger.error(f"{error_msg}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"{error_msg}: {str(e)}"
        )


# Setpoint command endpoints (POST)
@router.post("/gas/main/flow")
async def set_main_flow(request: Request, flow: GasFlowRequest):
    """Set main gas flow setpoint."""
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
    """Set feeder gas flow setpoint."""
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
    """Set feeder frequency setpoint."""
    try:
        await request.app.state.service.equipment.set_feeder_frequency(feeder_id, freq.frequency)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set feeder {feeder_id} frequency: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set feeder {feeder_id} frequency: {str(e)}"
        )


@router.post("/deagg/{deagg_id}/settings")
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


# State change endpoints (PUT)
@router.put("/gas/main/valve")
async def set_main_gas_valve(request: Request, valve: GasValveRequest):
    """Set main gas valve state."""
    try:
        await request.app.state.service.equipment.set_main_gas_valve(valve.open)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set main gas valve: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set main gas valve: {str(e)}"
        )


@router.put("/gas/feeder/valve")
async def set_feeder_gas_valve(request: Request, valve: GasValveRequest):
    """Set feeder gas valve state."""
    try:
        await request.app.state.service.equipment.set_feeder_gas_valve(valve.open)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set feeder gas valve: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set feeder gas valve: {str(e)}"
        )


@router.put("/vacuum/gate")
async def set_gate_valve(request: Request, valve: GateValveRequest):
    """Set gate valve position state."""
    try:
        await request.app.state.service.equipment.set_gate_valve_position(valve.position)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set gate valve: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set gate valve: {str(e)}"
        )


@router.put("/vacuum/mechanical_pump/state")
async def set_mech_pump_state(request: Request, pump: VacuumPumpRequest):
    """Set mechanical pump state."""
    try:
        if pump.start:
            await request.app.state.service.equipment.start_mech_pump()
        else:
            await request.app.state.service.equipment.stop_mech_pump()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set mechanical pump state: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set mechanical pump state: {str(e)}"
        )


@router.put("/vacuum/booster_pump/state")
async def set_booster_pump_state(request: Request, pump: VacuumPumpRequest):
    """Set booster pump state."""
    try:
        if pump.start:
            await request.app.state.service.equipment.start_booster_pump()
        else:
            await request.app.state.service.equipment.stop_booster_pump()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set booster pump state: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set booster pump state: {str(e)}"
        )


@router.put("/feeder/{feeder_id}/state")
async def set_feeder_state(request: Request, feeder_id: int, running: bool):
    """Set feeder running state."""
    try:
        if running:
            await request.app.state.service.equipment.start_feeder(feeder_id)
        else:
            await request.app.state.service.equipment.stop_feeder(feeder_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set feeder {feeder_id} state: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set feeder {feeder_id} state: {str(e)}"
        )


@router.put("/nozzle/select")
async def select_nozzle(request: Request, nozzle_id: Literal[1, 2]):
    """Set active nozzle state."""
    try:
        await request.app.state.service.equipment.select_nozzle(nozzle_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set nozzle selection: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set nozzle selection: {str(e)}"
        )


@router.put("/nozzle/shutter/state")
async def set_shutter_state(request: Request, shutter: ShutterRequest):
    """Set nozzle shutter state."""
    try:
        await request.app.state.service.equipment.set_shutter(shutter.open)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to set shutter state: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to set shutter state: {str(e)}"
        )
