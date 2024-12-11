import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router, init_router
from .service import MessagingService

app = FastAPI(
    title="Messaging API",
    description="API for pub/sub messaging",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
messaging_service = MessagingService()

# Initialize router
init_router(messaging_service)

# Register router
app.include_router(router)

@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    await messaging_service.start()

@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown."""
    await messaging_service.stop()

@app.get("/health")
async def health_check():
    """Check API health."""
    try:
        if messaging_service is None:
            return {
                "status": "Error",
                "error": "Service not initialized"
            }
        # Check message broker connection
        queue_size = await messaging_service.get_queue_size()
        if queue_size is None:
            return {
                "status": "Error",
                "error": "Message broker not connected"
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

if __name__ == "__main__":
    uvicorn.run(
        "micro_cold_spray.api.messaging.main:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    ) 