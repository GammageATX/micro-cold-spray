"""Configuration service FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from micro_cold_spray.core.config.router import router
from micro_cold_spray.core.config.service import ConfigService

# Create FastAPI app
app = FastAPI(
    title="Configuration Service",
    description="Service for managing configuration data using Dynaconf",
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

# Initialize service
config_service = ConfigService()

# Include config router
app.include_router(router)


# Add health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": config_service.get_environment(),
        "is_production": config_service.is_production()
    }
