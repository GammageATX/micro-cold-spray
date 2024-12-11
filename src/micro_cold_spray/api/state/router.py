"""FastAPI router for state management endpoints."""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from .service import StateService, StateTransitionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/state", tags=["state"])
_service: Optional[StateService] = None


def init_router(service: StateService) -> None:
    """Initialize the router with a state service instance."""
    global _service
    _service = service


def get_service() -> StateService:
    """Get the state service instance."""
    if _service is None:
        raise RuntimeError("State service not initialized")
    return _service


@router.get("/current")
async def get_current_state() -> Dict[str, str]:
    """
    Get the current system state.
    
    Returns:
        Dict containing current state name
    """
    service = get_service()
    return {"state": service.current_state}


@router.post("/transition/{target_state}")
async def transition_state(target_state: str) -> Dict[str, str]:
    """
    Transition to a new system state.
    
    Args:
        target_state: Name of the state to transition to
        
    Returns:
        Dict containing new state name
        
    Raises:
        HTTPException: If transition is invalid or fails
    """
    service = get_service()
    try:
        await service.transition_to(target_state.upper())
        return {"state": service.current_state}
    except StateTransitionError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to transition state: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/history")
async def get_state_history(
    limit: Optional[int] = Query(None, description="Optional limit on number of history entries")
) -> List[Dict[str, str]]:
    """
    Get state transition history.
    
    Args:
        limit: Optional limit on number of history entries to return
        
    Returns:
        List of state transition records
    """
    service = get_service()
    return service.get_state_history(limit)


@router.get("/valid-transitions")
async def get_valid_transitions() -> Dict[str, List[str]]:
    """
    Get map of valid state transitions.
    
    Returns:
        Dict mapping current states to lists of valid target states
    """
    service = get_service()
    return service.get_valid_transitions()


@router.get("/conditions")
async def get_state_conditions(
    state: Optional[str] = Query(None, description="Optional state to check conditions for")
) -> Dict[str, bool]:
    """
    Get conditions for a state.
    
    Args:
        state: Optional state to check conditions for, defaults to current state
        
    Returns:
        Dict of condition names to their current status
    """
    service = get_service()
    return await service.get_conditions(state)


@router.get("/health")
async def health_check(
    service: StateService = Depends(get_service)
):
    """Check API health status."""
    try:
        # Check state machine status
        status = await service.check_state_machine()
        if not status:
            return {
                "status": "Error",
                "error": "State machine error"
            }
        
        return {
            "status": "Running",
            "error": None
        }
    except Exception as e:
        return {
            "status": "Error",
            "error": str(e)
        } 