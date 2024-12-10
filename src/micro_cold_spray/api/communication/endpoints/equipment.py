from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from datetime import datetime

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

# ... other equipment endpoints
