"""FastAPI application for Communication API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router

app = FastAPI(
    title="MicroColdSpray Communication API",
    description="""
    API for hardware communication in the MicroColdSpray system.
    
    Features:
    - Tag reading and writing
    - Real-time tag values
    - Hardware control
    - Tag caching
    - Tag validation
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
    prefix="/api/communication",
    tags=["communication"]
)

# Health check
@app.get("/health")
async def health_check():
    """Check if the API is running."""
    return {
        "status": "ok",
        "service": "communication",
        "version": "1.0.0"
    } 