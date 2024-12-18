"""Process router."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from .service import ProcessService
from .models import ExecutionStatus, ActionStatus, ProcessPattern, ParameterSet
from ..base.exceptions import ProcessError, ServiceError
from ..base.errors import AppErrorCode, format_error
from ..config.singleton import get_config_service
from ..communication.service import CommunicationService
from ..messaging.service import MessagingService
from ..data_collection.service import DataCollectionService
from ..validation.service import ValidationService


class ServiceResponse(BaseModel):
    """Standard service response model."""
    status: str
    message: str
    timestamp: datetime


class SequenceResponse(BaseModel):
    """Sequence operation response model."""
    status: str
    sequence_id: Optional[str] = None
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service_name: str
    version: str
    is_running: bool
    timestamp: datetime


# Create router with prefix (app will handle the base /api/v1 prefix)
router = APIRouter(prefix="/process", tags=["process"])
_service: Optional[ProcessService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global _service
    try:
        # Get shared config service instance
        config_service = get_config_service()
        if not config_service.is_running:
            await config_service.start()
            if not config_service.is_running:
                raise ServiceError("ConfigService failed to start")
            logger.info("ConfigService started successfully")

        # Initialize required services
        message_broker = MessagingService(config_service=config_service)
        await message_broker.start()
        if not message_broker.is_running:
            raise ServiceError("MessagingService failed to start")
        logger.info("MessagingService started successfully")

        comm_service = CommunicationService(config_service=config_service)
        await comm_service.start()
        if not comm_service.is_running:
            raise ServiceError("CommunicationService failed to start")
        logger.info("CommunicationService started successfully")

        data_collection_service = DataCollectionService(config_service=config_service)
        await data_collection_service.start()
        if not data_collection_service.is_running:
            raise ServiceError("DataCollectionService failed to start")
        logger.info("DataCollectionService started successfully")

        validation_service = ValidationService(config_service=config_service)
        await validation_service.start()
        if not validation_service.is_running:
            raise ServiceError("ValidationService failed to start")
        logger.info("ValidationService started successfully")
        
        # Initialize process service with all dependencies
        _service = ProcessService(
            config_service=config_service,
            comm_service=comm_service,
            message_broker=message_broker,
            data_collection_service=data_collection_service,
            validation_service=validation_service
        )
        await _service.start()
        if not _service.is_running:
            raise ServiceError("ProcessService failed to start")
        logger.info("ProcessService started successfully")
        
        # Store service in app state for testing
        app.state.service = _service
        
        yield
        
    finally:
        # Cleanup on shutdown
        logger.info("Process API shutting down")
        if _service:
            try:
                await _service.stop()
                logger.info("Process service stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping process service: {e}")
            finally:
                _service = None
                app.state.service = None


# Create FastAPI app with lifespan
app = FastAPI(title="Process API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_service() -> ProcessService:
    """Get service instance."""
    if not _service or not _service.is_running:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, "ProcessService not initialized")
        )
    return _service


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not running"}
    }
)
async def health_check(service: ProcessService = Depends(get_service)):
    """Check service health."""
    try:
        # Directly check service health without storing result
        await service.check_health()
        return HealthResponse(
            status="ok" if service.is_running else "error",
            service_name=service._service_name,
            version=getattr(service, "version", "1.0.0"),
            is_running=service.is_running,
            timestamp=datetime.now()
        )
    except ProcessError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.PROCESS_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )


@router.post(
    "/sequence/start/{sequence_id}",
    response_model=SequenceResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid sequence"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def start_sequence(
    sequence_id: str,
    background_tasks: BackgroundTasks,
    service: ProcessService = Depends(get_service)
):
    """Start executing a sequence."""
    try:
        await service.start_sequence(sequence_id)
        background_tasks.add_task(logger.info, f"Started sequence {sequence_id}")
        
        return SequenceResponse(
            status="started",
            sequence_id=sequence_id,
            timestamp=datetime.now()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=format_error(AppErrorCode.INVALID_ACTION, str(e))
        )
    except ProcessError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.PROCESS_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )


@router.post(
    "/sequence/abort",
    response_model=ServiceResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Cannot abort sequence"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def abort_sequence(
    background_tasks: BackgroundTasks,
    service: ProcessService = Depends(get_service)
):
    """Abort current sequence."""
    try:
        await service.abort_sequence()
        background_tasks.add_task(logger.info, "Aborted current sequence")
        
        return ServiceResponse(
            status="ok",
            message="Sequence aborted successfully",
            timestamp=datetime.now()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=format_error(AppErrorCode.INVALID_ACTION, str(e))
        )
    except ProcessError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.PROCESS_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )


@router.get(
    "/sequence/status",
    response_model=ExecutionStatus,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def get_sequence_status(service: ProcessService = Depends(get_service)):
    """Get current sequence status."""
    try:
        sequence = await service.get_current_sequence()
        if not sequence:
            return ExecutionStatus(
                sequence_id="",
                status="inactive",
                current_step=0,
                total_steps=0,
                start_time=datetime.now()
            )
            
        return ExecutionStatus(
            sequence_id=sequence["id"],
            status=sequence["status"],
            current_step=sequence["current_step"],
            total_steps=len(sequence["sequence"]["steps"]),
            start_time=datetime.fromisoformat(sequence["start_time"]),
            end_time=datetime.fromisoformat(sequence["end_time"]) if "end_time" in sequence else None,
            error=sequence.get("error"),
            progress=sequence["current_step"] / len(sequence["sequence"]["steps"]) * 100
        )
    except ProcessError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.PROCESS_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )


@router.get(
    "/sequences",
    response_model=List[Dict[str, Any]],
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def list_sequences(service: ProcessService = Depends(get_service)):
    """List available sequences."""
    try:
        return await service.list_sequences()
    except ProcessError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.PROCESS_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )


@router.get(
    "/patterns",
    response_model=List[ProcessPattern],
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def list_patterns(service: ProcessService = Depends(get_service)):
    """List available patterns."""
    try:
        return await service.list_patterns()
    except ProcessError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.PROCESS_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )


@router.get(
    "/parameters",
    response_model=List[ParameterSet],
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def list_parameter_sets(service: ProcessService = Depends(get_service)):
    """List available parameter sets."""
    try:
        return await service.list_parameter_sets()
    except ProcessError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.PROCESS_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )


@router.get(
    "/action/status",
    response_model=Optional[ActionStatus],
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def get_action_status(service: ProcessService = Depends(get_service)):
    """Get current action status."""
    try:
        action = await service.get_current_action()
        if not action:
            return None
            
        return ActionStatus(
            action_type=action["type"],
            parameters=action["parameters"],
            status=action["status"],
            start_time=datetime.fromisoformat(action["start_time"]),
            end_time=datetime.fromisoformat(action["end_time"]) if "end_time" in action else None,
            error=action.get("error"),
            progress=action.get("progress", 0.0),
            data=action.get("data", {})
        )
    except ProcessError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.PROCESS_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )


# Include router in app
app.include_router(router, prefix="/api/v1")
