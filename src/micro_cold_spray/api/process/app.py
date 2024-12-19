# src/micro_cold_spray/api/process/app.py
from ..base.app import BaseApp
from .service import ProcessService
from .router import router

# Create process app
app = BaseApp(
    service_class=ProcessService,
    title="Process API",
    description="Process control and monitoring endpoints",
    version="1.0.0",
    dependencies=[
        "config_service",
        "comm_service",
        "message_service",
        "data_service",
        "validation_service"
    ]
).app

# Include process router
app.include_router(router)
