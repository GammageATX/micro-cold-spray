"""FastAPI router for process operations."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from .service import ProcessService
from .exceptions import ProcessError

router = APIRouter(prefix="/process", tags=["process"])
_service: Optional[ProcessService] = None


def init_router(service: ProcessService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service


def get_service() -> ProcessService:
    """Get process service instance."""
    if _service is None:
        raise RuntimeError("Process service not initialized")
    return _service


@router.post("/sequence/start/{sequence_id}")
async def start_sequence(sequence_id: str) -> Dict[str, str]:
    """Start executing a sequence.
    
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


@router.post("/sequence/cancel")
async def cancel_sequence() -> Dict[str, str]:
    """Cancel current sequence.
    
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


@router.get("/sequence/status")
async def get_sequence_status() -> Dict[str, Any]:
    """Get current sequence status.
    
    Returns:
        Dict containing sequence status
    """
    service = get_service()
    active_sequence = service.active_sequence
    
    if not active_sequence:
        return {"status": "inactive"}
        
    return {
        "status": "active",
        "sequence_id": active_sequence,
        "step": service.sequence_step
    }


@router.post("/patterns/generate")
async def generate_pattern(pattern_request: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a new pattern.
    
    Args:
        pattern_request: Pattern generation parameters
        
    Returns:
        Dict containing generated pattern data
    """
    service = get_service()
    try:
        pattern = await service.generate_pattern(
            pattern_request.get("type"),
            pattern_request.get("parameters", {})
        )
        return {
            "status": "success",
            "pattern": pattern
        }
    except ProcessError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to generate pattern: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/patterns/{pattern_id}/validate")
async def validate_pattern(pattern_id: str) -> Dict[str, Any]:
    """Validate a pattern.
    
    Args:
        pattern_id: ID of pattern to validate
        
    Returns:
        Dict containing validation results
    """
    service = get_service()
    try:
        await service.validate_pattern(pattern_id)
        return {
            "status": "success",
            "message": "Pattern validation passed"
        }
    except ProcessError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to validate pattern: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/sequences/create")
async def create_sequence(sequence_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new sequence.
    
    Args:
        sequence_data: Sequence definition data
        
    Returns:
        Dict containing created sequence ID
    """
    service = get_service()
    try:
        sequence_id = await service.create_sequence(sequence_data)
        return {"sequence_id": sequence_id}
    except ProcessError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to create sequence: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/parameters/create")
async def create_parameter_set(parameter_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new parameter set.
    
    Args:
        parameter_data: Parameter set definition
        
    Returns:
        Dict containing created parameter set ID
    """
    service = get_service()
    try:
        param_id = await service.create_parameter_set(parameter_data)
        return {"parameter_id": param_id}
    except ProcessError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to create parameter set: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/files/parameters")
async def list_parameter_files() -> Dict[str, Any]:
    """List available parameter files.
    
    Returns:
        Dict containing list of parameter files
    """
    service = get_service()
    try:
        files = await service.list_parameter_files()
        return {"files": files}
    except ProcessError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to list parameter files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/files/patterns")
async def list_pattern_files() -> Dict[str, Any]:
    """List available pattern files.
    
    Returns:
        Dict containing list of pattern files
    """
    service = get_service()
    try:
        files = await service.list_pattern_files()
        return {"files": files}
    except ProcessError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to list pattern files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/files/sequences")
async def list_sequence_files() -> Dict[str, Any]:
    """List available sequence files.
    
    Returns:
        Dict containing list of sequence files
    """
    service = get_service()
    try:
        files = await service.list_sequence_files()
        return {"files": files}
    except ProcessError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to list sequence files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/health")
async def health_check(
    service: ProcessService = Depends(get_service)
) -> Dict[str, Any]:
    """Check API health status.
    
    Returns:
        Dict containing health status
    """
    try:
        if not service.is_running:
            return {
                "status": "error",
                "message": "Service not running"
            }
            
        return {
            "status": "ok",
            "message": "Service healthy"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
