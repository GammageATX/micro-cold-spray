"""FastAPI router for process operations."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import APIRouter, HTTPException, BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .service import ProcessService
from .exceptions import (
    ProcessError,
    SequenceError
)
from .models import (
    ExecutionStatus,
    ActionStatus,
    ProcessPattern,
    ParameterSet
)
from ..base.router import add_health_endpoints
from ..config.singleton import get_config_service

# Create router without prefix (app already handles the /process prefix)
router = APIRouter(tags=["process"])
_service: Optional[ProcessService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global _service
    try:
        # Get shared config service instance
        config_service = get_config_service()
        await config_service.start()
        logger.info("ConfigService started successfully")
        
        # Initialize process service
        _service = ProcessService(config_service=config_service)
        await _service.start()
        logger.info("ProcessService started successfully")
        
        # Add health endpoints
        add_health_endpoints(app, _service)
        # Mount router to app
        app.include_router(router)
        logger.info("Process router initialized")
        
        yield
        
        # Cleanup on shutdown
        logger.info("Process API shutting down")
        if _service:
            try:
                await _service.stop()
                logger.info("Process service stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping process service: {e}")
            
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Attempt cleanup
        if _service and _service.is_running:
            await _service.stop()
        raise


# Create FastAPI app with lifespan
app = FastAPI(title="Process API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_service() -> ProcessService:
    """Get process service instance."""
    if _service is None:
        logger.error("Process service not initialized")
        raise RuntimeError("Process service not initialized")
    return _service


@router.get("/health")
async def health_check() -> JSONResponse:
    """Check API and service health status."""
    service = get_service()
    
    try:
        status = {
            "status": "ok" if service.is_running else "error",
            "service_info": {
                "name": service._service_name,
                "version": getattr(service, "version", "1.0.0"),
                "running": service.is_running
            },
            "sequence": await service.get_current_sequence(),
            "timestamp": datetime.now().isoformat()
        }
        
        if not service.is_running:
            status["status"] = "error"
            status["error"] = "Service not running"
            return JSONResponse(
                status_code=503,
                content=status
            )
            
        return JSONResponse(status)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": str(e),
                "service_info": {
                    "name": service._service_name,
                    "running": False
                },
                "timestamp": datetime.now().isoformat()
            }
        )


@router.post("/sequence/start/{sequence_id}", response_model=Dict[str, Any])
async def start_sequence(
    sequence_id: str,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Start executing a sequence.
    
    Args:
        sequence_id: ID of sequence to execute
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict containing operation status
        
    Raises:
        HTTPException: If sequence cannot be started
    """
    service = get_service()
    
    try:
        await service.start_sequence(sequence_id)
        background_tasks.add_task(
            logger.info,
            f"Started sequence {sequence_id}"
        )
        
        return {
            "status": "started",
            "sequence_id": sequence_id,
            "timestamp": datetime.now().isoformat()
        }
    except SequenceError as e:
        logger.error(f"Failed to start sequence: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/sequence/abort", response_model=Dict[str, Any])
async def abort_sequence(
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Abort current sequence.
    
    Args:
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict containing operation status
        
    Raises:
        HTTPException: If sequence cannot be aborted
    """
    service = get_service()
    
    try:
        await service.abort_sequence()
        background_tasks.add_task(
            logger.info,
            "Aborted current sequence"
        )
        
        return {
            "status": "aborted",
            "timestamp": datetime.now().isoformat()
        }
    except ProcessError as e:
        logger.error(f"Failed to abort sequence: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/sequence/status", response_model=ExecutionStatus)
async def get_sequence_status() -> ExecutionStatus:
    """Get current sequence status.
    
    Returns:
        Current sequence execution status
        
    Raises:
        HTTPException: If status cannot be retrieved
    """
    service = get_service()
    
    try:
        sequence = await service.get_current_sequence()
        if not sequence:
            return ExecutionStatus(
                sequence_id="",
                status="inactive",
                current_step=0,
                total_steps=0,
                start_time=datetime.now()
            )
            
        return ExecutionStatus(
            sequence_id=sequence["id"],
            status=sequence["status"],
            current_step=sequence["current_step"],
            total_steps=len(sequence["sequence"]["steps"]),
            start_time=datetime.fromisoformat(sequence["start_time"]),
            end_time=datetime.fromisoformat(sequence["end_time"]) if "end_time" in sequence else None,
            error=sequence.get("error"),
            progress=sequence["current_step"] / len(sequence["sequence"]["steps"]) * 100
        )
    except Exception as e:
        logger.error(f"Failed to get sequence status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/sequences", response_model=List[Dict[str, Any]])
async def list_sequences() -> List[Dict[str, Any]]:
    """List available sequences.
    
    Returns:
        List of sequences with metadata
        
    Raises:
        HTTPException: If sequences cannot be retrieved
    """
    service = get_service()
    
    try:
        sequences = await service.list_sequences()
        return sequences
    except ProcessError as e:
        logger.error(f"Failed to list sequences: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/patterns", response_model=List[ProcessPattern])
async def list_patterns() -> List[ProcessPattern]:
    """List available patterns.
    
    Returns:
        List of patterns with metadata
        
    Raises:
        HTTPException: If patterns cannot be retrieved
    """
    service = get_service()
    
    try:
        patterns = await service.list_patterns()
        return patterns
    except ProcessError as e:
        logger.error(f"Failed to list patterns: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/parameters", response_model=List[ParameterSet])
async def list_parameter_sets() -> List[ParameterSet]:
    """List available parameter sets.
    
    Returns:
        List of parameter sets with metadata
        
    Raises:
        HTTPException: If parameter sets cannot be retrieved
    """
    service = get_service()
    
    try:
        parameter_sets = await service.list_parameter_sets()
        return parameter_sets
    except ProcessError as e:
        logger.error(f"Failed to list parameter sets: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/action/status", response_model=Optional[ActionStatus])
async def get_action_status() -> Optional[ActionStatus]:
    """Get current action status.
    
    Returns:
        Current action status or None if no action is running
        
    Raises:
        HTTPException: If status cannot be retrieved
    """
    service = get_service()
    
    try:
        action = await service.get_current_action()
        if not action:
            return None
            
        return ActionStatus(
            action_type=action["type"],
            parameters=action["parameters"],
            status=action["status"],
            start_time=datetime.fromisoformat(action["start_time"]),
            end_time=datetime.fromisoformat(action["end_time"]) if "end_time" in action else None,
            error=action.get("error"),
            progress=action.get("progress", 0.0),
            data=action.get("data", {})
        )
    except Exception as e:
        logger.error(f"Failed to get action status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )
