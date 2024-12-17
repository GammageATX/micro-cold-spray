"""State management router."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .service import StateService
from .models import StateRequest, StateResponse, StateTransition
from .exceptions import InvalidStateError, StateTransitionError, ConditionError
from ..base.router import add_health_endpoints
from ..base.errors import ErrorCode, format_error
from ..config.singleton import get_config_service
from ..messaging.service import MessagingService
from ..communication.service import CommunicationService

# Create router without prefix (app already handles the /state prefix)
router = APIRouter(tags=["state"])

_service: Optional[StateService] = None


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
        
        # Load valid topics from application config
        config = await config_service.get_config("application")
        services_config = config.data.get("services", {})
        message_config = services_config.get("message_broker", {})
        topic_groups = message_config.get("topics", {})
        
        # Flatten topic groups into a set of valid topics
        valid_topics = set()
        for group in topic_groups.values():
            valid_topics.update(group)
            
        # Set valid topics before using messaging
        await message_broker.set_valid_topics(valid_topics)
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
        
        # Add health endpoints
        add_health_endpoints(app, _service)
        # Mount router to app with prefix
        app.include_router(router, prefix="/state")
        logger.info("State router initialized")
        
        yield  # Application runs here
        
        # Cleanup on shutdown
        logger.info("State API shutting down")
        if _service:
            try:
                await _service.stop()
                logger.info("State service stopped successfully")
                _service = None
            except Exception as e:
                logger.error(f"Error stopping state service: {e}")
                
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Attempt cleanup of any partially initialized services
        if _service and _service.is_running:
            await _service.stop()
        raise

# Create FastAPI app with lifespan
app = FastAPI(title="State API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_state_service() -> StateService:
    """Get state service instance."""
    if _service is None:
        error = ErrorCode.SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=503,  # Service Unavailable
            detail=format_error(error, "State service not initialized")["detail"]
        )
    return _service


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
        error = ErrorCode.SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=503,  # Service Unavailable
            detail=format_error(error, "State service not initialized")["detail"]
        )
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=500,  # Internal Server Error
            detail=format_error(error, str(e))["detail"]
        )


@router.get("/conditions", response_model=Dict[str, Any])
async def get_conditions(
    state: Optional[str] = Query(None),
    service: StateService = Depends(get_state_service)
) -> Dict[str, Any]:
    """Get conditions for a state."""
    try:
        if state == "":
            error = ErrorCode.VALIDATION_ERROR
            raise HTTPException(
                status_code=422,  # Unprocessable Entity
                detail=format_error(error, "Empty state parameter")["detail"]
            )
        conditions = await service.get_conditions(state)
        if isinstance(conditions, dict):  # Handle async mock response
            return {
                "state": state or service.current_state,
                "conditions": conditions,
                "timestamp": datetime.now().isoformat()
            }
        return await conditions  # Handle coroutine response
    except InvalidStateError as e:
        logger.error(f"Invalid state: {e}")
        error = ErrorCode.INVALID_STATE
        raise HTTPException(
            status_code=400,  # Bad Request
            detail=format_error(error, "Invalid state")["detail"]
        )
    except ConditionError as e:
        logger.error(f"Condition check failed: {e}")
        error = ErrorCode.CONDITION_ERROR
        # Extract failed conditions directly from the error
        failed_conditions = e.conditions["failed_conditions"] if isinstance(e.conditions, dict) and "failed_conditions" in e.conditions else []
        raise HTTPException(
            status_code=400,  # Bad Request
            detail=format_error(error, str(e), {"failed_conditions": failed_conditions})["detail"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conditions: {e}")
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=500,  # Internal Server Error
            detail=format_error(error, str(e))["detail"]
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
            error = ErrorCode.VALIDATION_ERROR
            raise HTTPException(
                status_code=422,  # Unprocessable Entity
                detail=format_error(error, "Empty target state")["detail"]
            )
        if request.reason and len(request.reason) > 500:
            error = ErrorCode.VALIDATION_ERROR
            raise HTTPException(
                status_code=422,  # Unprocessable Entity
                detail=format_error(error, "Reason too long (max 500 characters)")["detail"]
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
    except InvalidStateError as e:
        logger.error(f"Invalid state requested: {e}")
        error = ErrorCode.INVALID_STATE
        raise HTTPException(
            status_code=400,  # Bad Request
            detail=format_error(error, str(e))["detail"]
        )
    except StateTransitionError as e:
        logger.error(f"Transition failed: {e}")
        error = ErrorCode.STATE_TRANSITION_ERROR
        raise HTTPException(
            status_code=409,  # Conflict
            detail=format_error(error, str(e))["detail"]
        )
    except ConditionError as e:
        logger.error(f"Conditions not met: {e}")
        error = ErrorCode.CONDITION_ERROR
        # Get the failed conditions list directly from the error
        failed_conditions = e.conditions.get("failed_conditions", []) if isinstance(e.conditions, dict) else []
        raise HTTPException(
            status_code=400,  # Bad Request
            detail=format_error(error, str(e), {"failed_conditions": failed_conditions})["detail"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=500,  # Internal Server Error
            detail=format_error(error, str(e))["detail"]
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
    except HTTPException:
        raise
    except ValueError:  # Removed unused 'as e'
        # Return FastAPI's standard validation error format
        raise HTTPException(
            status_code=422,
            detail=[{
                "loc": ["query", "limit"],
                "msg": "value is not a valid integer",
                "type": "type_error.integer"
            }]
        ) from None  # Suppress the original exception
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=500,  # Internal Server Error
            detail=format_error(error, str(e))["detail"]
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
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=500,  # Internal Server Error
            detail=format_error(error, str(e))["detail"]
        )


# Add startup and shutdown events for testing
async def startup():
    """Initialize services on startup."""
    global _service
    
    try:
        # Get shared config service instance
        config_service = get_config_service()
        await config_service.start()
        logger.info("ConfigService started successfully")
        
        # Initialize message broker
        message_broker = MessagingService(config_service=config_service)
        await message_broker.start()
        
        # Load valid topics from application config
        config = await config_service.get_config("application")
        services_config = config.data.get("services", {})
        message_config = services_config.get("message_broker", {})
        topic_groups = message_config.get("topics", {})
        
        # Flatten topic groups into a set of valid topics
        valid_topics = set()
        for group in topic_groups.values():
            valid_topics.update(group)
            
        # Set valid topics before using messaging
        await message_broker.set_valid_topics(valid_topics)
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
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        if _service and _service.is_running:
            await _service.stop()
        raise e  # Re-raise the exception to ensure test catches it


async def shutdown():
    """Handle shutdown tasks."""
    global _service
    if _service:
        try:
            await _service.stop()
            _service = None
        except Exception as e:
            logger.error(f"Error stopping state service: {e}")
            # Don't re-raise the exception to allow clean shutdown

# Add startup and shutdown events to router for testing
router.startup = startup
router.shutdown = shutdown
