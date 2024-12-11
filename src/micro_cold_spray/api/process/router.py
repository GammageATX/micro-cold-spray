"""FastAPI router for process operations."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging

from .service import ProcessService, ProcessError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/process", tags=["process"])
_service: Optional[ProcessService] = None


def init_router(service: ProcessService) -> None:
    """Initialize router with service instance.
    
    Args:
        service: Process service instance
    """
    global _service
    _service = service


def get_service() -> ProcessService:
    """Get process service instance.
    
    Returns:
        ProcessService instance
        
    Raises:
        RuntimeError: If service not initialized
    """
    if _service is None:
        raise RuntimeError("Process service not initialized")
    return _service


@router.post("/sequences/{sequence_id}/start")
async def start_sequence(sequence_id: str) -> Dict[str, str]:
    """Start executing a sequence.
    
    Args:
        sequence_id: ID of sequence to execute
        
    Returns:
        Dictionary containing:
            - status: Operation status
            - sequence_id: ID of started sequence
            
    Raises:
        HTTPException: If sequence cannot be started
    """
    service = get_service()
    try:
        await service.start_sequence(sequence_id)
        return {
            "status": "started",
            "sequence_id": sequence_id
        }
    except ProcessError as e:
        logger.warning(f"Failed to start sequence: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to start sequence: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start sequence: {str(e)}"
        )


@router.post("/sequences/cancel")
async def cancel_sequence() -> Dict[str, str]:
    """Cancel the current sequence.
    
    Returns:
        Dictionary containing:
            - status: Operation status
            
    Raises:
        HTTPException: If sequence cannot be cancelled
    """
    service = get_service()
    try:
        await service.cancel_sequence()
        return {"status": "cancelled"}
    except ProcessError as e:
        logger.warning(f"Failed to cancel sequence: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to cancel sequence: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel sequence: {str(e)}"
        )


@router.get("/sequences/status")
async def get_sequence_status() -> Dict[str, Any]:
    """Get current sequence status.
    
    Returns:
        Dictionary containing:
            - active_sequence: ID of active sequence if any
            - step: Current step number
    """
    service = get_service()
    try:
        return {
            "active_sequence": service.active_sequence,
            "step": service.sequence_step
        }
    except Exception as e:
        logger.error(f"Failed to get sequence status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sequence status: {str(e)}"
        )


@router.post("/patterns/generate")
async def generate_pattern(pattern_request: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a new pattern.
    
    Args:
        pattern_request: Pattern generation parameters
        
    Returns:
        Dictionary containing:
            - status: Operation status
            - pattern: Generated pattern data
            
    Raises:
        HTTPException: If pattern cannot be generated
    """
    service = get_service()
    try:
        pattern = await service.generate_pattern(pattern_request)
        return {"status": "success", "pattern": pattern}
    except ProcessError as e:
        logger.warning(f"Failed to generate pattern: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to generate pattern: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate pattern: {str(e)}"
        )


@router.post("/patterns/{pattern_id}/validate")
async def validate_pattern(pattern_id: str) -> Dict[str, Any]:
    """Validate a pattern.
    
    Args:
        pattern_id: ID of pattern to validate
        
    Returns:
        Dictionary containing:
            - status: Operation status
            - validation: Validation results
            
    Raises:
        HTTPException: If pattern cannot be validated
    """
    service = get_service()
    try:
        result = await service.validate_pattern(pattern_id)
        return {"status": "success", "validation": result}
    except ProcessError as e:
        logger.warning(f"Failed to validate pattern: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to validate pattern: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate pattern: {str(e)}"
        )


@router.post("/sequences/create")
async def create_sequence(sequence_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new sequence.
    
    Args:
        sequence_data: Sequence definition data
        
    Returns:
        Dictionary containing:
            - sequence_id: ID of created sequence
            
    Raises:
        HTTPException: If sequence cannot be created
    """
    service = get_service()
    try:
        sequence_id = await service.create_sequence(sequence_data)
        return {"sequence_id": sequence_id}
    except ProcessError as e:
        logger.warning(f"Failed to create sequence: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to create sequence: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create sequence: {str(e)}"
        )


@router.post("/parameters/create")
async def create_parameter_set(parameter_data: Dict[str, Any]) -> Dict[str, str]:
    """Create a new parameter set.
    
    Args:
        parameter_data: Parameter set definition
        
    Returns:
        Dictionary containing:
            - parameter_id: ID of created parameter set
            
    Raises:
        HTTPException: If parameter set cannot be created
    """
    service = get_service()
    try:
        param_id = await service.create_parameter_set(parameter_data)
        return {"parameter_id": param_id}
    except ProcessError as e:
        logger.warning(f"Failed to create parameter set: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to create parameter set: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create parameter set: {str(e)}"
        )


@router.get("/files/parameters")
async def list_parameter_files() -> Dict[str, Any]:
    """List available parameter files.
    
    Returns:
        Dictionary containing:
            - files: List of parameter file names
    """
    service = get_service()
    try:
        files = await service.list_parameter_files()
        return {"files": files}
    except Exception as e:
        logger.error(f"Failed to list parameter files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list parameter files: {str(e)}"
        )


@router.get("/files/patterns")
async def list_pattern_files() -> Dict[str, Any]:
    """List available pattern files.
    
    Returns:
        Dictionary containing:
            - files: List of pattern file names
    """
    service = get_service()
    try:
        files = await service.list_pattern_files()
        return {"files": files}
    except Exception as e:
        logger.error(f"Failed to list pattern files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list pattern files: {str(e)}"
        )


@router.get("/files/sequences")
async def list_sequence_files() -> Dict[str, Any]:
    """List available sequence files.
    
    Returns:
        Dictionary containing:
            - files: List of sequence file names
    """
    service = get_service()
    try:
        files = await service.list_sequence_files()
        return {"files": files}
    except Exception as e:
        logger.error(f"Failed to list sequence files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sequence files: {str(e)}"
        )


@router.get("/health")
async def health_check(
    service: ProcessService = Depends(get_service)
) -> Dict[str, Any]:
    """Check API health status.
    
    Returns:
        Dictionary containing:
            - status: Service status
            - error: Error message if any
    """
    try:
        if not service.is_running:
            return {
                "status": "Error",
                "error": "Service not running"
            }
            
        return {
            "status": "Running",
            "error": None
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "Error",
            "error": str(e)
        }
