import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .router import router, init_router
from .service import ConfigService
from ...core.infrastructure.messaging.message_broker import MessageBroker

app = FastAPI(
    title="Config API",
    description="API for configuration management",
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

# Initialize services
config_path = Path("config")
message_broker = MessageBroker()

# Initialize config service
config_service = ConfigService(
    config_path=config_path,
    message_broker=message_broker
)

# Initialize router
init_router(config_service)

# Register router
app.include_router(router)


@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    await message_broker.start()
    await config_service.start()


@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown."""
    await config_service.stop()
    await message_broker.stop()


if __name__ == "__main__":
    uvicorn.run(
        "micro_cold_spray.api.config.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    ) 