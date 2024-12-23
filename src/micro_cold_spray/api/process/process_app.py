# src/micro_cold_spray/api/process/process_app.py
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.endpoints.process_endpoints import ProcessRouter, HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for service initialization and cleanup."""
    try:
        # Initialize services
        app.state.process_service = ProcessService()
        await app.state.process_service.initialize()
        await app.state.process_service.start()
        
        logger.info("Process service initialized")
        
        yield  # Run application
        
        # Cleanup
        if hasattr(app.state, "process_service"):
            await app.state.process_service.stop()
            
        logger.info("Process service stopped")
        
    except Exception as e:
        logger.error(f"Service lifecycle error: {e}")
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"Service lifecycle error: {str(e)}"
        )


def create_app() -> FastAPI:
    """Create process service application.
    
    Returns:
        FastAPI application instance
    """
    # Create FastAPI app
    app = FastAPI(
        title="Process Service",
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Add root health endpoint
    @app.get(
        "/health",
        response_model=HealthResponse,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
        }
    )
    async def health_check() -> HealthResponse:
        """Check service health status."""
        try:
            return HealthResponse(
                status="ok" if app.state.process_service.is_running else "error",
                is_running=app.state.process_service.is_running,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Health check failed: {str(e)}"
            )

    # Add process endpoints
    process_router = ProcessRouter(app.state.process_service)
    app.include_router(
        process_router.router,
        prefix="/api/process",
        tags=["process"]
    )
    
    return app
