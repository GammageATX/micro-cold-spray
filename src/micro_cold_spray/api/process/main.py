"""Process API entry point."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router, init_router
from .service import ProcessService
from ..data_collection import init_api as init_data_collection


app = FastAPI(
    title="Process API",
    description="API for process control and sequence execution",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure from settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core services
config_manager = ConfigManager()
message_broker = MessageBroker()

# Initialize data collection service
data_collection_service = init_data_collection(
    message_broker=message_broker,
    config_manager=config_manager
)

# Initialize process service
process_service = ProcessService(
    config_manager=config_manager,
    message_broker=message_broker,
    data_collection_service=data_collection_service
)

# Initialize router
init_router(process_service)

# Register router
app.include_router(router)


@app.on_event("startup")
async def startup():
    """Initialize services on application startup."""
    await config_manager.start()
    await message_broker.start()
    await data_collection_service.start()
    await process_service.start()


@app.on_event("shutdown")
async def shutdown():
    """Clean up services on application shutdown."""
    await process_service.stop()
    await data_collection_service.stop()
    await message_broker.stop()
    await config_manager.stop()


@app.get("/health")
async def health_check():
    """Check API health."""
    try:
        # Check if service is initialized
        if process_service is None:
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


if __name__ == "__main__":
    uvicorn.run(
        "micro_cold_spray.api.process.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
