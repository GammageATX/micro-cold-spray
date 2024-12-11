"""FastAPI application for State API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router

app = FastAPI(
    title="MicroColdSpray State API",
    description="""
    API for managing system state in the MicroColdSpray system.
    
    Features:
    - State transitions with validation
    - State history tracking
    - Condition monitoring
    - State validation rules
    - Event notifications
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(
    router,
    prefix="/api/state",
    tags=["state"]
)


# Health check
@app.get("/health")
async def health_check():
    """Check API health."""
    try:
        if state_service is None:
            return {
                "status": "Error",
                "error": "Service not initialized"
            }
        return {
            "status": "Running",
            "error": None
        }
    except Exception as e:
        return {
            "status": "Error",
            "error": str(e)
        }
