# src/micro_cold_spray/__main__.py
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import service applications
from micro_cold_spray.core.config.app import app as config_app
from micro_cold_spray.core.communication.app import app as communication_app
from micro_cold_spray.core.process.app import app as process_app
from micro_cold_spray.core.state.app import app as state_app
from micro_cold_spray.core.data_collection.app import app as data_collection_app
from micro_cold_spray.core.validation.app import app as validation_app
from micro_cold_spray.core.messaging.app import app as messaging_app
from micro_cold_spray.ui.app import app as ui_app

# Create main FastAPI application
app = FastAPI(
    title="Micro Cold Spray Control System",
    description="Monolithic API for micro cold spray control system",
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

# Mount service applications
app.mount("/api/config", config_app)
app.mount("/api/communication", communication_app)
app.mount("/api/process", process_app)
app.mount("/api/state", state_app)
app.mount("/api/data", data_collection_app)
app.mount("/api/validation", validation_app)
app.mount("/api/messaging", messaging_app)
app.mount("/ui", ui_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
