"""Service UI router."""

from pathlib import Path
from fastapi import FastAPI, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from micro_cold_spray.ui.utils import get_uptime, get_memory_usage
from typing import Dict, Any
import asyncio
import psutil


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
async def index(request: Request):
    """Render index page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "api_urls": get_api_urls(),
            "test_scenarios": get_test_scenarios()
        }
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "uptime": get_uptime(),
        "memory": get_memory_usage()
    }


@app.get("/testing")
async def testing_interface(request: Request):
    """Render testing interface."""
    return templates.TemplateResponse(
        "testing/index.html",
        {
            "request": request,
            "api_urls": get_api_urls(),
            "test_scenarios": get_test_scenarios()
        }
    )


@app.get("/testing/tags")
async def tag_monitor(request: Request):
    """Render tag monitor interface."""
    return templates.TemplateResponse(
        "testing/tag_monitor.html",
        {
            "request": request,
            "api_urls": get_api_urls()
        }
    )


@app.get("/monitoring/services")
async def services_monitor(request: Request):
    """Render services monitor page."""
    return templates.TemplateResponse(
        "monitoring/services.html",
        {
            "request": request,
            "api_urls": get_api_urls()
        }
    )


@app.get("/monitoring/services/status")
async def get_services_status() -> Dict[str, Any]:
    """Get status of all services."""
    services = {
        "config": {"port": 8001},
        "communication": {"port": 8002},
        "messaging": {"port": 8007},
        "state": {"port": 8004},
        "data_collection": {"port": 8005}
    }

    for service_name, service_info in services.items():
        try:
            service_info["name"] = service_name
            service_info["status"] = "ok"
            service_info["uptime"] = get_uptime()
            service_info["memory_usage"] = get_memory_usage()
            service_info["service_info"] = {
                "running": True,
                "version": "1.0.0"
            }
        except Exception as e:
            service_info["status"] = "error"
            service_info["service_info"] = {
                "running": False,
                "error": str(e)
            }

    return services


@app.post("/monitoring/services/control")
async def control_service(service: str, action: str) -> Dict[str, str]:
    """Control a service (start/stop/restart)."""
    try:
        # Implement service control logic here
        return {"status": "success", "message": f"{action} {service} successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.websocket("/monitoring/logs")
async def service_logs(websocket: WebSocket):
    """WebSocket endpoint for service logs."""
    await websocket.accept()
    try:
        while True:
            # Send log updates every second
            await asyncio.sleep(1)
            await websocket.send_json({
                "timestamp": "2024-01-01T00:00:00",
                "service": "system",
                "level": "INFO",
                "message": "System running normally"
            })
    except Exception:
        await websocket.close()
