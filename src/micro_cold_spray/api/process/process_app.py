# src/micro_cold_spray/api/process/process_app.py
from fastapi import FastAPI, status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.endpoints.process_endpoints import ProcessRouter


async def create_app() -> FastAPI:
    """Create FastAPI application.
    
    Returns:
        FastAPI application
        
    Raises:
        HTTPException: If application creation fails (503)
    """
    try:
        app = FastAPI(title="Process Management API")
        
        # Create and initialize services
        process_service = ProcessService()
        await process_service.initialize()
        await process_service.start()
        
        # Create and mount routers
        process_router = ProcessRouter(process_service)
        app.include_router(process_router.router)
        
        return app
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Failed to create process application",
            context={"error": str(e)},
            cause=e
        )
