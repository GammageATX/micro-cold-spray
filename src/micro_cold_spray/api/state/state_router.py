"""State management router."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base import add_health_endpoints
from micro_cold_spray.api.config import get_config_service
from micro_cold_spray.api.messaging.messaging_service import MessagingService
from micro_cold_spray.api.communication.communication_service import CommunicationService
from .state_service import StateService
from .state_models import StateRequest, StateResponse, StateTransition

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
        
        # Add health endpoints
        add_health_endpoints(app, _service)
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
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Failed to initialize state API",
            context={"error": str(e)},
            cause=e
        )


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


def get_service() -> StateService:
    """Get state service instance."""
    if _service is None:
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="State service not initialized"
        )
    return _service


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
