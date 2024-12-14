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


def init_router(service: StateService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service
    # Add health endpoints
    add_health_endpoints(app, service)
    # Mount router to app with prefix
    app.include_router(router, prefix="/state")
    logger.info("State router initialized with service")


def get_state_service() -> StateService:
    """Get state service instance."""
    if _service is None:
        raise HTTPException(
            status_code=503,
            detail="State service not initialized"
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
        logger.error(f"Failed to get status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/conditions", response_model=Dict[str, Any])
async def get_conditions(
    state: Optional[str] = None,
    service: StateService = Depends(get_state_service)
) -> Dict[str, Any]:
    """Get conditions for a state."""
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


@router.post("/transition", response_model=StateResponse)
async def transition_state(
    request: StateRequest,
    background_tasks: BackgroundTasks,
    service: StateService = Depends(get_state_service)
) -> StateResponse:
    """Request state transition."""
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
async def get_history(
    limit: Optional[int] = None,
    service: StateService = Depends(get_state_service)
) -> List[StateTransition]:
    """Get state transition history."""
    try:
        return service.get_state_history(limit)
    except Exception as e:
        logger.error(f"Failed to get history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/transitions", response_model=Dict[str, List[str]])
async def get_transitions(
    service: StateService = Depends(get_state_service)
) -> Dict[str, List[str]]:
    """Get valid state transitions."""
    try:
        return service.get_valid_transitions()
    except Exception as e:
        logger.error(f"Failed to get transitions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("State API starting up")
    global _service
    if _service is None:
        try:
            # Get config service instance
            from ..config.service import ConfigService
            config_service = ConfigService()
            await config_service.start()
            logger.info("Config service started")
            
            # Get messaging service instance
            from ..messaging.service import MessagingService
            message_broker = MessagingService(config_service=config_service)
            await message_broker.start()
            logger.info("Messaging service started")
            
            # Get communication service instance
            from ..communication.service import CommunicationService
            communication_service = CommunicationService()
            communication_service._config_service = config_service
            await communication_service.start()
            logger.info("Communication service started")
            
            # Create and initialize state service
            _service = StateService(
                config_service=config_service,
                message_broker=message_broker,
                communication_service=communication_service
            )
            await _service.start()
            
            # Initialize router with service
            init_router(_service)
            logger.info("State API initialized and ready")
        except Exception as e:
            logger.error(f"Failed to start state service: {e}")
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
