"""Communication router."""

from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .service import CommunicationService
from ..base.router import add_health_endpoints
from ..base.errors import ErrorCode, format_error
from ..config.singleton import get_config_service

# Create router without prefix (app already handles the /communication prefix)
router = APIRouter(tags=["communication"])

_service: Optional[CommunicationService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global _service
    
    try:
        # Get shared config service instance
        config_service = get_config_service()
        await config_service.start()
        logger.info("ConfigService started successfully")
        
        # Initialize communication service
        _service = CommunicationService(config_service=config_service)
        await _service.start()
        logger.info("CommunicationService started successfully")
        
        # Add health endpoints
        add_health_endpoints(app, _service)
        # Mount router to app with prefix
        app.include_router(router, prefix="/communication")
        logger.info("Communication router initialized")
        
        yield  # Application runs here
        
        # Cleanup on shutdown
        logger.info("Communication API shutting down")
        if _service:
            try:
                await _service.stop()
                logger.info("Communication service stopped successfully")
                _service = None
            except Exception as e:
                logger.error(f"Error stopping communication service: {e}")
                
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Attempt cleanup of any partially initialized services
        if _service and _service.is_running:
            await _service.stop()
        raise

# Create FastAPI app with lifespan
app = FastAPI(title="Communication API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_communication_service() -> CommunicationService:
    """Get communication service instance."""
    if _service is None:
        error = ErrorCode.SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=503,  # Service Unavailable
            detail=format_error(error, "Communication service not initialized")["detail"]
        )
    return _service


def init_router(service: CommunicationService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service
    # Add health endpoints
    add_health_endpoints(router, service)


# Add startup and shutdown events for testing
async def startup():
    """Initialize services on startup."""
    global _service
    
    try:
        # Get shared config service instance
        config_service = get_config_service()
        await config_service.start()
        logger.info("ConfigService started successfully")
        
        # Initialize communication service
        _service = CommunicationService(config_service=config_service)
        await _service.start()
        logger.info("CommunicationService started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        if _service and _service.is_running:
            await _service.stop()
        raise e


async def shutdown():
    """Handle shutdown tasks."""
    global _service
    if _service:
        try:
            await _service.stop()
            _service = None
        except Exception as e:
            logger.error(f"Error stopping communication service: {e}")

# Add startup and shutdown events to router for testing
router.startup = startup
router.shutdown = shutdown
