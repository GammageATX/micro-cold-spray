"""Messaging service FastAPI application."""

from fastapi import FastAPI, APIRouter, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from micro_cold_spray.core.messaging.router import router, lifespan
from micro_cold_spray.core.base.models.health import HealthResponse
from micro_cold_spray.core.errors import AppErrorCode, format_error

# Create FastAPI app with lifespan
app = FastAPI(
    title="Messaging API",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add health endpoint at root level
health_router = APIRouter()


@health_router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Service is not running",
            "model": dict
        }
    }
)
async def health_check() -> HealthResponse:
    """Check service health status."""
    service = getattr(app.state, "service", None)
    if not service or not service.is_running:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_UNAVAILABLE, "Service is not running")
        )
    
    return HealthResponse(
        status="ok",
        service_name="messaging",
        version=getattr(service, "version", "1.0.0"),
        is_running=True,
        message="Messaging service is healthy"
    )

app.include_router(health_router)

# Include messaging router without /api/v1 prefix
app.include_router(router)
