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