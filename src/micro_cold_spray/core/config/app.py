"""Configuration service FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter

from micro_cold_spray.core.config.router import router, init_router
from micro_cold_spray.core.config.services.config_service import ConfigService
from micro_cold_spray.core.base.router import add_health_endpoints

# Create FastAPI app
app = FastAPI(
    title="Configuration Service",
    description="Service for managing configuration data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service and router
service = ConfigService()
init_router(service)

# Add health endpoints directly to app (not under /config prefix)
health_router = APIRouter()
add_health_endpoints(health_router, service)
app.include_router(health_router)

# Include config router
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    await service.start()
