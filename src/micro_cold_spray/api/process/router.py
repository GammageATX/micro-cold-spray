"""FastAPI router for process operations."""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException

from .service import ProcessService, ProcessError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/process", tags=["process"])
_service: Optional[ProcessService] = None


def init_router(service: ProcessService) -> None:
    """Initialize the router with a process service instance."""
    global _service
    _service = service


def get_service() -> ProcessService:
    """Get the process service instance."""
    if _service is None:
        raise RuntimeError("Process service not initialized")
    return _service


@router.post("/sequences/{sequence_id}/start")
@router.post("/sequences/{sequence_id}/stop")
@router.get("/sequences/status")
@router.post("/patterns/generate")
@router.post("/patterns/{pattern_id}/validate")
@router.get("/files/parameters")
@router.get("/files/patterns")
@router.get("/files/sequences")
async def start_sequence(sequence_id: str) -> Dict[str, str]:
    """
    Start executing a sequence.
    
    Args:
        sequence_id: ID of sequence to execute
        
    Returns:
        Dict containing operation status
    """
    service = get_service()
    try:
        await service.start_sequence(sequence_id)
        return {
            "status": "started",
            "sequence_id": sequence_id
        }
    except ProcessError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to start sequence: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/sequences/cancel")
async def cancel_sequence() -> Dict[str, str]:
    """
    Cancel the current sequence.
    
    Returns:
        Dict containing operation status
    """
    service = get_service()
    try:
        await service.cancel_sequence()
        return {"status": "cancelled"}
    except ProcessError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to cancel sequence: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/sequences/status")
async def get_sequence_status() -> Dict[str, Any]:
    """
    Get current sequence status.
    
    Returns:
        Dict containing sequence status
    """
    service = get_service()
    return {
        "active_sequence": service.active_sequence,
        "step": service.sequence_step
    }


@router.post("/patterns/generate")
async def generate_pattern(pattern_request: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a new pattern."""
    service = get_service()
    try:
        pattern = await service.generate_pattern(pattern_request)
        return {"status": "success", "pattern": pattern}
    except ProcessError as e:
        raise HTTPException(status_code=400, detail={"error": str(e), "context": e.context})


@router.post("/patterns/{pattern_id}/validate")
async def validate_pattern(pattern_id: str) -> Dict[str, Any]:
    """Validate a pattern."""
    service = get_service()
    try:
        result = await service.validate_pattern(pattern_id)
        return {"status": "success", "validation": result}
    except ProcessError as e:
        raise HTTPException(status_code=400, detail={"error": str(e), "context": e.context})


@router.post("/sequences/create")
async def create_sequence(sequence_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new sequence."""
    service = get_service()
    sequence_id = await service.create_sequence(sequence_data)
    return {"sequence_id": sequence_id}


@router.post("/actions/groups")
async def define_action_group(group_data: Dict[str, Any]) -> Dict[str, str]:
    """Define a new action group."""
    service = get_service()
    await service.define_action_group(group_data)
    return {"status": "created"}


@router.post("/parameters/create")
async def create_parameter_set(parameter_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new parameter set."""
    service = get_service()
    param_id = await service.create_parameter_set(parameter_data)
    return {"parameter_id": param_id}


@router.get("/files/parameters")
async def list_parameter_files() -> Dict[str, Any]:
    """List available parameter files."""
    service = get_service()
    files = await service.list_parameter_files()
    return {"files": files}


@router.get("/files/patterns")
async def list_pattern_files() -> Dict[str, Any]:
    """List available pattern files."""
    service = get_service()
    files = await service.list_pattern_files()
    return {"files": files}


@router.get("/files/sequences")
async def list_sequence_files() -> Dict[str, Any]:
    """List available sequence files."""
    service = get_service()
    files = await service.list_sequence_files()
    return {"files": files} 