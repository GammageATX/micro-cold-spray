"""State management router."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, BackgroundTasks, Depends, Query
from loguru import logger

from .services import StateService
from .models import StateRequest, StateResponse, StateTransition
from micro_cold_spray.core.errors.codes import AppErrorCode
from micro_cold_spray.core.errors.formatting import raise_http_error
from micro_cold_spray.core.errors.exceptions import ValidationError, StateError
from micro_cold_spray.core.base import create_service_dependency
from ..config import get_config_service
from ..messaging import MessagingService
from ..communication import CommunicationService

# Create router without prefix (app already handles the /state prefix)
router = APIRouter(tags=["state"])
_service: Optional[StateService] = None


def init_router(service: StateService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global _service
    try:
        # Get shared config service instance
        config_service = get_config_service()
        await config_service.start()
        logger.info("ConfigService started successfully")
        
        # Initialize message broker
        message_broker = MessagingService(config_service=config_service)
        await message_broker.start()
        logger.info("MessagingService started successfully")
        
        # Initialize communication service
        communication_service = CommunicationService(config_service=config_service)
        await communication_service.start()
        logger.info("CommunicationService started successfully")
        
        # Initialize state service
        _service = StateService(
            config_service=config_service,
            message_broker=message_broker,
            communication_service=communication_service
        )
        await _service.start()
        logger.info("StateService started successfully")
        
        # Mount router to app
        app.include_router(router)
        logger.info("State router initialized")
        
        yield
        
        # Cleanup on shutdown
        logger.info("State API shutting down")
        if _service:
            try:
                await _service.stop()
                logger.info("State service stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping state service: {e}")
            finally:
                _service = None
            
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Attempt cleanup
        if _service and _service.is_running:
            await _service.stop()
            _service = None
        raise


# Create dependency for StateService
get_state_service = create_service_dependency(StateService)


@router.get("/status", response_model=Dict[str, Any])
async def get_status(
    service: StateService = Depends(get_state_service)
) -> Dict[str, Any]:
    """Get current state status."""
    try:
        return {
            "state": service.current_state,
            "timestamp": datetime.now().isoformat()
        }
    except AttributeError:
        raise_http_error(
            AppErrorCode.SERVICE_UNAVAILABLE,
            "State service not initialized"
        )
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise_http_error(
            AppErrorCode.SERVICE_ERROR,
            str(e)
        )


@router.get("/conditions", response_model=Dict[str, Any])
async def get_conditions(
    state: Optional[str] = Query(None),
    service: StateService = Depends(get_state_service)
) -> Dict[str, Any]:
    """Get conditions for a state."""
    try:
        if state == "":
            raise_http_error(
                AppErrorCode.VALIDATION_ERROR,
                "Empty state parameter"
            )
        conditions = await service.get_conditions(state)
        if isinstance(conditions, dict):  # Handle async mock response
            return {
                "state": state or service.current_state,
                "conditions": conditions,
                "timestamp": datetime.now().isoformat()
            }
        return await conditions  # Handle coroutine response
    except StateError as e:
        logger.error(f"State error: {e}")
        raise_http_error(
            AppErrorCode.INVALID_REQUEST,
            str(e),
            e.context
        )
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise_http_error(
            AppErrorCode.VALIDATION_ERROR,
            str(e),
            e.context
        )
    except Exception as e:
        logger.error(f"Failed to get conditions: {e}")
        raise_http_error(
            AppErrorCode.SERVICE_ERROR,
            str(e)
        )


@router.post("/transition", response_model=StateResponse)
async def transition_state(
    request: StateRequest,
    background_tasks: BackgroundTasks,
    service: StateService = Depends(get_state_service)
) -> StateResponse:
    """Request state transition."""
    try:
        if not request.target_state:
            raise_http_error(
                AppErrorCode.VALIDATION_ERROR,
                "Empty target state"
            )
        if request.reason and len(request.reason) > 500:
            raise_http_error(
                AppErrorCode.VALIDATION_ERROR,
                "Reason too long (max 500 characters)"
            )
        response = await service.transition_to(request)
        if isinstance(response, StateResponse):  # Handle async mock response
            if response.success:
                background_tasks.add_task(
                    logger.info,
                    f"State transitioned from {response.old_state} to {response.new_state}"
                )
            return response
        return await response  # Handle coroutine response
    except StateError as e:
        logger.error(f"State error: {e}")
        raise_http_error(
            AppErrorCode.INVALID_REQUEST,
            str(e),
            e.context
        )
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise_http_error(
            AppErrorCode.VALIDATION_ERROR,
            str(e),
            e.context
        )
    except Exception as e:
        logger.error(f"Failed to transition state: {e}")
        raise_http_error(
            AppErrorCode.SERVICE_ERROR,
            str(e)
        )


@router.get("/history", response_model=List[StateTransition])
async def get_history(
    limit: Optional[int] = Query(
        None,
        description="Maximum number of history entries to return",
        ge=0
    ),
    service: StateService = Depends(get_state_service)
) -> List[StateTransition]:
    """Get state transition history."""
    try:
        history = service.get_state_history(limit)
        if isinstance(history, list):  # Handle async mock response
            return history
        return await history  # Handle coroutine response
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise_http_error(
            AppErrorCode.VALIDATION_ERROR,
            str(e),
            e.context
        )
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise_http_error(
            AppErrorCode.SERVICE_ERROR,
            str(e)
        )


@router.get("/transitions", response_model=Dict[str, List[str]])
async def get_transitions(
    service: StateService = Depends(get_state_service)
) -> Dict[str, List[str]]:
    """Get valid state transitions."""
    try:
        transitions = service.get_valid_transitions()
        if isinstance(transitions, dict):  # Handle async mock response
            return transitions
        return await transitions  # Handle coroutine response
    except Exception as e:
        logger.error(f"Failed to get transitions: {e}")
        raise_http_error(
            AppErrorCode.SERVICE_ERROR,
            str(e)
        )
