"""State management router."""

from typing import Dict, List
from fastapi import APIRouter, HTTPException, Depends

from ..base import get_service
from .service import StateService
from .models import StateRequest, StateResponse, StateTransition
from .exceptions import StateError, InvalidStateError


router = APIRouter(prefix="/state", tags=["state"])


def init_router() -> None:
    """Initialize state router."""
    pass


@router.get("/current")
async def get_current_state(
    service: StateService = Depends(get_service(StateService))
) -> Dict[str, str]:
    """Get current state.
    
    Returns:
        Dictionary with current state name
    """
    return {"state": service.current_state}


@router.post("/transition")
async def transition_state(
    request: StateRequest,
    service: StateService = Depends(get_service(StateService))
) -> StateResponse:
    """Request state transition.
    
    Args:
        request: State transition request
        
    Returns:
        State transition response
        
    Raises:
        HTTPException: If transition fails
    """
    try:
        return await service.transition_to(request)
    except InvalidStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_state_history(
    limit: int | None = None,
    service: StateService = Depends(get_service(StateService))
) -> List[StateTransition]:
    """Get state transition history.
    
    Args:
        limit: Optional limit on number of entries to return
        
    Returns:
        List of state transition records
    """
    return service.get_state_history(limit)


@router.get("/transitions")
async def get_valid_transitions(
    service: StateService = Depends(get_service(StateService))
) -> Dict[str, List[str]]:
    """Get map of valid state transitions.
    
    Returns:
        Dictionary mapping current states to lists of valid target states
    """
    return service.get_valid_transitions()


@router.get("/conditions")
async def get_state_conditions(
    state: str | None = None,
    service: StateService = Depends(get_service(StateService))
) -> Dict[str, bool]:
    """Get conditions for a state.
    
    Args:
        state: Optional state to check conditions for, defaults to current state
        
    Returns:
        Dictionary mapping condition names to their current status
        
    Raises:
        HTTPException: If state not found
    """
    try:
        return await service.get_conditions(state)
    except InvalidStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StateError as e:
        raise HTTPException(status_code=500, detail=str(e))
