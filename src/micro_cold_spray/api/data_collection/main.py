"""Data Collection API entry point."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router, init_router
from .service import DataCollectionService


app = FastAPI(
    title="Data Collection API",
    description="API for managing data collection during process execution",
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
service = DataCollectionService(
    message_broker=message_broker,
    config_manager=config_manager
)

# Initialize router
init_router(service)

# Register router
app.include_router(router)


@app.on_event("startup")
async def startup():
    """Initialize services on application startup."""
    await config_manager.start()
    await message_broker.start()
    await service.start()


@app.on_event("shutdown")
async def shutdown():
    """Clean up services on application shutdown."""
    await service.stop()
    await message_broker.stop()
    await config_manager.stop()


@app.get("/health")
async def health_check():
    """Check API health."""
    try:
        if service is None:
            return {
                "status": "Error",
                "error": "Service not initialized"
            }
        # Check storage access
        storage_ok = await service._spray_storage is not None
        if not storage_ok:
            return {
                "status": "Error",
                "error": "Storage not accessible"
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


def init_api(
    message_broker: MessageBroker,
    config_manager: ConfigManager
) -> DataCollectionService:
    """
    Initialize the Data Collection service for use by other APIs.
    
    Args:
        message_broker: Message broker instance
        config_manager: Config manager instance
        
    Returns:
        Initialized DataCollectionService instance
    """
    return DataCollectionService(
        message_broker=message_broker,
        config_manager=config_manager
    )


if __name__ == "__main__":
    uvicorn.run(
        "micro_cold_spray.api.data_collection.main:app",
        host="0.0.0.0",
        port=8001,  # Different port than Process API
        reload=True
    )
