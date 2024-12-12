"""State management router."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger

from .service import StateService
from .models import StateRequest, StateResponse, StateTransition
from .exceptions import InvalidStateError, StateTransitionError, ConditionError

router = APIRouter(prefix="/state", tags=["state"])
_service: Optional[StateService] = None


def init_router(service: StateService) -> None:
    """Initialize router with service instance.
    
    Args:
        service: State service instance
    """
    global _service
    _service = service


def get_service() -> StateService:
    """Get state service instance.
    
    Returns:
        StateService instance
        
    Raises:
        RuntimeError: If service not initialized
    """
    if _service is None:
        logger.error("State service not initialized")
        raise RuntimeError("State service not initialized")
    return _service


@router.get("/status", response_model=Dict[str, Any])
async def get_status() -> Dict[str, Any]:
    """Get current state status.
    
    Returns:
        Dict containing current state and timestamp
        
    Raises:
        HTTPException: If status cannot be retrieved
    """
    service = get_service()
    
    try:
        return {
            "state": service.current_state,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/transition", response_model=StateResponse)
async def transition_state(
    request: StateRequest,
    background_tasks: BackgroundTasks
) -> StateResponse:
    """Request state transition.
    
    Args:
        request: State transition request
        background_tasks: FastAPI background tasks
        
    Returns:
        State transition response
        
    Raises:
        HTTPException: If transition fails
    """
    service = get_service()
    
    try:
        response = await service.transition_to(request)
        if response.success:
            background_tasks.add_task(
                logger.info,
                f"State transitioned from {response.old_state} to {response.new_state}"
            )
        return response
        
    except InvalidStateError as e:
        logger.error(f"Invalid state requested: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid state", "message": str(e)}
        )
    except StateTransitionError as e:
        logger.error(f"Transition failed: {str(e)}")
        raise HTTPException(
            status_code=409,
            detail={"error": "Transition failed", "message": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/history", response_model=List[StateTransition])
async def get_state_history(limit: Optional[int] = None) -> List[StateTransition]:
    """Get state transition history.
    
    Args:
        limit: Optional limit on number of entries to return
        
    Returns:
        List of state transition records
        
    Raises:
        HTTPException: If history cannot be retrieved
    """
    service = get_service()
    
    try:
        return service.get_state_history(limit)
    except Exception as e:
        logger.error(f"Failed to get history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/transitions", response_model=Dict[str, List[str]])
async def get_valid_transitions() -> Dict[str, List[str]]:
    """Get map of valid state transitions.
    
    Returns:
        Dict mapping current states to lists of valid target states
        
    Raises:
        HTTPException: If transitions cannot be retrieved
    """
    service = get_service()
    
    try:
        return service.get_valid_transitions()
    except Exception as e:
        logger.error(f"Failed to get transitions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/conditions", response_model=Dict[str, Any])
async def get_state_conditions(state: Optional[str] = None) -> Dict[str, Any]:
    """Get conditions for a state.
    
    Args:
        state: Optional state to check conditions for, defaults to current state
        
    Returns:
        Dict mapping condition names to their current status
        
    Raises:
        HTTPException: If conditions cannot be retrieved
    """
    service = get_service()
    
    try:
        conditions = await service.get_conditions(state)
        return {
            "state": state or service.current_state,
            "conditions": conditions,
            "timestamp": datetime.now().isoformat()
        }
    except InvalidStateError as e:
        logger.error(f"Invalid state: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid state", "message": str(e)}
        )
    except ConditionError as e:
        logger.error(f"Condition check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Condition check failed", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to get conditions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/health")
async def health_check() -> JSONResponse:
    """Check API and service health status.
    
    Returns:
        JSON response with health status
        
    Note:
        Returns 503 if service unhealthy
    """
    service = get_service()
    
    try:
        status = {
            "service": "ok" if service.is_running else "error",
            "state": service.current_state,
            "timestamp": datetime.now().isoformat()
        }
        
        if not service.is_running:
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
                "service": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
