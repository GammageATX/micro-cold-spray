"""Service UI router."""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from micro_cold_spray.ui.utils import get_uptime, get_memory_usage


app = FastAPI(title="MicroColdSpray UI")

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static"
)

# Setup templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def get_api_urls():
    """Get API URLs for templates."""
    return {
        "config": "http://localhost:8001",
        "communication": "http://localhost:8002",
        "messaging": "http://localhost:8007",
        "state": "http://localhost:8004",
        "data_collection": "http://localhost:8005",
        "ws": {
            "messaging": "ws://localhost:8007/messaging/subscribe",
            "state": "ws://localhost:8004/state/monitor",
            "tags": "ws://localhost:8002/communication/tags",
            "services": "ws://localhost:8000/monitoring/logs"
        }
    }


def get_test_scenarios():
    """Get available test scenarios."""
    return {
        "motion": {
            "name": "Motion System Test",
            "description": "Test motion control system",
            "steps": ["home", "move_x", "move_y", "move_z"]
        },
        "gas": {
            "name": "Gas Control Test",
            "description": "Test gas control system",
            "steps": ["valve_open", "set_flow", "valve_close"]
        }
    }


@app.get("/")
async def home(request: Request):
    """Render home page."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"api_urls": get_api_urls()}
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "uptime": get_uptime(),
        "memory": get_memory_usage()
    }


@app.get("/testing")
async def testing_interface(request: Request):
    """Render testing interface."""
    return templates.TemplateResponse(
        request=request,
        name="testing/index.html",
        context={
            "api_urls": get_api_urls(),
            "test_scenarios": get_test_scenarios()
        }
    )
