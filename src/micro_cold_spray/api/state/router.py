"""FastAPI router for state management endpoints."""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, List, Optional, Any
import logging

from .service import StateService, StateTransitionError

logger = logging.getLogger(__name__)

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
        raise RuntimeError("State service not initialized")
    return _service


@router.get("/current")
async def get_current_state() -> Dict[str, str]:
    """Get the current system state.
    
    Returns:
        Dictionary containing:
            - state: Current state name
    """
    service = get_service()
    try:
        return {"state": service.current_state}
    except Exception as e:
        logger.error(f"Failed to get current state: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get current state: {str(e)}"
        )


@router.post("/transition/{target_state}")
async def transition_state(target_state: str) -> Dict[str, str]:
    """Transition to a new system state.
    
    Args:
        target_state: Name of the state to transition to
        
    Returns:
        Dictionary containing:
            - state: New state name
        
    Raises:
        HTTPException: If transition is invalid or fails
    """
    service = get_service()
    try:
        await service.transition_to(target_state.upper())
        return {"state": service.current_state}
    except StateTransitionError as e:
        logger.warning(f"Invalid state transition: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to transition state: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to transition state: {str(e)}"
        )


@router.get("/history")
async def get_state_history(
    limit: Optional[int] = Query(None, description="Optional limit on number of history entries")
) -> List[Dict[str, str]]:
    """Get state transition history.
    
    Args:
        limit: Optional limit on number of history entries to return
        
    Returns:
        List of dictionaries containing:
            - state: State name
            - timestamp: Transition timestamp
            - reason: Transition reason (if any)
    """
    service = get_service()
    try:
        return service.get_state_history(limit)
    except Exception as e:
        logger.error(f"Failed to get state history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get state history: {str(e)}"
        )


@router.get("/valid-transitions")
async def get_valid_transitions() -> Dict[str, List[str]]:
    """Get map of valid state transitions.
    
    Returns:
        Dictionary mapping current states to lists of valid target states
    """
    service = get_service()
    try:
        return service.get_valid_transitions()
    except Exception as e:
        logger.error(f"Failed to get valid transitions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get valid transitions: {str(e)}"
        )


@router.get("/conditions")
async def get_state_conditions(
    state: Optional[str] = Query(None, description="Optional state to check conditions for")
) -> Dict[str, bool]:
    """Get conditions for a state.
    
    Args:
        state: Optional state to check conditions for, defaults to current state
        
    Returns:
        Dictionary mapping condition names to their current status
    """
    service = get_service()
    try:
        return await service.get_conditions(state)
    except Exception as e:
        logger.error(f"Failed to get state conditions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get state conditions: {str(e)}"
        )


@router.get("/health")
async def health_check(
    service: StateService = Depends(get_service)
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