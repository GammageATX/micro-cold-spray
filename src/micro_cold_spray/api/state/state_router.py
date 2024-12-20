"""State management router."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from .state_service import StateService
from .state_models import StateRequest, StateResponse, StateTransition


# Create router
router = APIRouter(tags=["state"])


def get_service() -> StateService:
    """Get state service instance."""
    if not hasattr(get_service, "_service"):
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="State service not initialized"
        )
    return get_service._service


@router.get("/status", response_model=Dict[str, Any])
async def get_status(
    service: StateService = Depends(get_service)
) -> Dict[str, Any]:
    """Get current state status."""
    try:
        return {
            "state": service.current_state,
            "timestamp": datetime.now().isoformat()
        }
    except AttributeError:
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="State service not initialized"
        )
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to get status",
            context={"error": str(e)},
            cause=e
        )


@router.get("/conditions", response_model=Dict[str, Any])
async def get_conditions(
    state: Optional[str] = Query(None),
    service: StateService = Depends(get_service)
) -> Dict[str, Any]:
    """Get conditions for a state."""
    try:
        if state == "":
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Empty state parameter"
            )
        conditions = await service.get_conditions(state)
        return {
            "state": state or service.current_state,
            "conditions": conditions,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to get conditions",
            context={"error": str(e)},
            cause=e
        )


@router.post("/transition", response_model=StateResponse)
async def transition_state(
    request: StateRequest,
    background_tasks: BackgroundTasks,
    service: StateService = Depends(get_service)
) -> StateResponse:
    """Request state transition."""
    try:
        if not request.target_state:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Empty target state"
            )
        if request.reason and len(request.reason) > 500:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Reason too long (max 500 characters)"
            )
        response = await service.transition_to(request)
        if response.success:
            background_tasks.add_task(
                logger.info,
                f"State transitioned from {response.old_state} to {response.new_state}"
            )
        return response
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to transition state",
            context={"error": str(e)},
            cause=e
        )


@router.get("/history", response_model=List[StateTransition])
async def get_history(
    limit: Optional[int] = Query(
        None,
        description="Maximum number of history entries to return",
        ge=0
    ),
    service: StateService = Depends(get_service)
) -> List[StateTransition]:
    """Get state transition history."""
    try:
        return service.get_state_history(limit)
    except ValueError:
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Invalid limit parameter"
        )
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to get history",
            context={"error": str(e)},
            cause=e
        )


@router.get("/transitions", response_model=Dict[str, List[str]])
async def get_transitions(
    service: StateService = Depends(get_service)
) -> Dict[str, List[str]]:
    """Get valid state transitions."""
    try:
        return service.get_valid_transitions()
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to get transitions",
            context={"error": str(e)},
            cause=e
        )
