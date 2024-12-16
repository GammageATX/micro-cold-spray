"""State management router."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .service import StateService
from .models import StateRequest, StateResponse, StateTransition
from .exceptions import InvalidStateError, StateTransitionError, ConditionError
from ..base.router import add_health_endpoints
from ..config.singleton import get_config_service
from ..messaging.service import MessagingService
from ..communication.service import CommunicationService

# Create FastAPI app
app = FastAPI(title="State API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create router without prefix (app already handles the /state prefix)
router = APIRouter(tags=["state"])

_service: Optional[StateService] = None


@app.on_event("startup")
async def startup_event():
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
        
        # Add health endpoints
        add_health_endpoints(app, _service)
        # Mount router to app with prefix
        app.include_router(router, prefix="/state")
        logger.info("State router initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Attempt cleanup of any partially initialized services
        if _service and _service.is_running:
            await _service.stop()
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Handle shutdown tasks."""
    logger.info("State API shutting down")
    if _service:
        try:
            await _service.stop()
            logger.info("State service stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping state service: {e}")


def get_state_service() -> StateService:
    """Get state service instance."""
    if _service is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "Service Unavailable", "message": "State service not initialized"}
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
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal Server Error", "message": str(e)}
        )


@router.get("/conditions", response_model=Dict[str, Any])
async def get_conditions(
    state: Optional[str] = None,
    service: StateService = Depends(get_state_service)
) -> Dict[str, Any]:
    """Get conditions for a state."""
    try:
        if state == "":
            raise HTTPException(
                status_code=422,
                detail={"error": "Validation Error", "message": "Empty state parameter"}
            )
        conditions = await service.get_conditions(state)
        return {
            "state": state or service.current_state,
            "conditions": conditions,
            "timestamp": datetime.now().isoformat()
        }
    except InvalidStateError as e:
        logger.error(f"Invalid state: {e}")
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid State", "message": str(e)}
        )
    except ConditionError as e:
        logger.error(f"Condition check failed: {e}")
        raise HTTPException(
            status_code=400,
            detail={"error": "Condition Error", "message": str(e), "data": e.data}
        )
    except Exception as e:
        logger.error(f"Failed to get conditions: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal Server Error", "message": str(e)}
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
            raise HTTPException(
                status_code=422,
                detail={"error": "Validation Error", "message": "Empty target state"}
            )
        if len(request.reason) > 500:
            raise HTTPException(
                status_code=422,
                detail={"error": "Validation Error", "message": "Reason too long"}
            )
        response = await service.transition_to(request)
        if response.success:
            background_tasks.add_task(
                logger.info,
                f"State transitioned from {response.old_state} to {response.new_state}"
            )
        return response
    except InvalidStateError as e:
        logger.error(f"Invalid state requested: {e}")
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid State", "message": str(e)}
        )
    except StateTransitionError as e:
        logger.error(f"Transition failed: {e}")
        raise HTTPException(
            status_code=409,
            detail={"error": "State Transition Error", "message": str(e)}
        )
    except ConditionError as e:
        logger.error(f"Conditions not met: {e}")
        raise HTTPException(
            status_code=400,
            detail={"error": "Condition Error", "message": str(e), "data": e.data}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal Server Error", "message": str(e)}
        )


@router.get("/history", response_model=List[StateTransition])
async def get_history(
    limit: Optional[int] = None,
    service: StateService = Depends(get_state_service)
) -> List[StateTransition]:
    """Get state transition history."""
    try:
        if limit is not None:
            if limit < 0:
                raise HTTPException(
                    status_code=422,
                    detail={"error": "Validation Error", "message": "Limit must be non-negative"}
                )
        history = await service.get_state_history(limit)
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal Server Error", "message": str(e)}
        )


@router.get("/transitions", response_model=Dict[str, List[str]])
async def get_transitions(
    service: StateService = Depends(get_state_service)
) -> Dict[str, List[str]]:
    """Get valid state transitions."""
    try:
        transitions = await service.get_valid_transitions()
        return transitions
    except Exception as e:
        logger.error(f"Failed to get transitions: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal Server Error", "message": str(e)}
        )
