"""Communication service FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter

from micro_cold_spray.core.communication.router import router, lifespan
from micro_cold_spray.core.base.router import add_health_endpoints

# Create FastAPI app with lifespan
app = FastAPI(
    title="Communication Service",
    description="Service for handling equipment communication and tag management",
    version="1.0.0",
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

# Include communication router without /api/v1 prefix
app.include_router(router)

# Add health endpoints at root level
health_router = APIRouter()


@app.on_event("startup")
async def startup_event():
    """Initialize services and add health endpoints."""
    # Add health endpoints after service is initialized in lifespan
    add_health_endpoints(health_router, app.state.service)
    app.include_router(health_router)
